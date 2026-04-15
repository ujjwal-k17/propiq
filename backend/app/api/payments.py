"""
Payments API
============
POST /payments/create-order  — create a Razorpay order, returns order_id + key
POST /payments/verify        — verify payment signature, activate subscription
POST /payments/webhook       — Razorpay webhook handler (signature-verified)
GET  /payments/history       — current user's payment history
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import razorpay
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models.payment import BillingCycle, Payment, PaymentStatus
from app.models.user import SubscriptionTier, User
from app.schemas.payment import (
    CreateOrderRequest,
    CreateOrderResponse,
    PaymentRecord,
    VerifyPaymentRequest,
)
from app.schemas.user import UserProfile

router = APIRouter(prefix="/payments", tags=["Payments"])

# ── Plan pricing (amount in paise, currency INR) ─────────────────────────────
# ₹499/mo, ₹399/mo billed annually (×12), ₹999/mo, ₹799/mo billed annually
_PLAN_PRICES: dict[tuple[str, str], int] = {
    ("basic", "monthly"):  49_900,    # ₹499
    ("basic", "annual"):  478_800,    # ₹399 × 12
    ("pro",   "monthly"):  99_900,    # ₹999
    ("pro",   "annual"):  958_800,    # ₹799 × 12
}

_SUBSCRIPTION_DURATION: dict[str, timedelta] = {
    "monthly": timedelta(days=30),
    "annual":  timedelta(days=365),
}


def _razorpay_client() -> razorpay.Client:
    return razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )


def _verify_payment_signature(
    order_id: str, payment_id: str, signature: str
) -> bool:
    """Verify Razorpay payment signature (HMAC-SHA256)."""
    body = f"{order_id}|{payment_id}"
    expected = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
        body.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def _verify_webhook_signature(raw_body: bytes, received: str) -> bool:
    """Verify Razorpay webhook signature (HMAC-SHA256 of raw body)."""
    expected = hmac.new(
        settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, received)


async def _activate_subscription(
    user: User,
    plan: str,
    billing_cycle: str,
    db: AsyncSession,
) -> None:
    """
    Set user.subscription_tier and extend subscription_expires_at.
    If subscription hasn't expired yet, extend from current expiry date.
    """
    now = datetime.now(timezone.utc)
    current_expiry = user.subscription_expires_at

    if current_expiry and current_expiry.tzinfo is None:
        current_expiry = current_expiry.replace(tzinfo=timezone.utc)

    base = current_expiry if (current_expiry and current_expiry > now) else now
    new_expiry = base + _SUBSCRIPTION_DURATION[billing_cycle]

    user.subscription_tier = SubscriptionTier(plan)
    user.subscription_expires_at = new_expiry
    await db.commit()
    await db.refresh(user)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/create-order", response_model=CreateOrderResponse)
async def create_order(
    body: CreateOrderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CreateOrderResponse:
    """Create a Razorpay order and persist a Payment record."""
    amount = _PLAN_PRICES.get((body.plan, body.billing_cycle))
    if amount is None:
        raise HTTPException(status_code=400, detail="Invalid plan or billing cycle.")

    payment_id = uuid.uuid4()

    # Create Razorpay order (sync SDK → run in thread)
    def _create() -> dict[str, Any]:
        client = _razorpay_client()
        return client.order.create(
            {
                "amount": amount,
                "currency": "INR",
                "receipt": str(payment_id),
                "notes": {
                    "plan": body.plan,
                    "billing_cycle": body.billing_cycle,
                    "user_id": str(current_user.id),
                },
            }
        )

    try:
        rz_order: dict[str, Any] = await asyncio.to_thread(_create)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Razorpay error: {exc}") from exc

    # Persist Payment record
    payment = Payment(
        id=payment_id,
        user_id=current_user.id,
        razorpay_order_id=rz_order["id"],
        plan=body.plan,
        billing_cycle=BillingCycle(body.billing_cycle),
        amount_paise=amount,
        currency="INR",
        status=PaymentStatus.created,
    )
    db.add(payment)
    await db.commit()

    return CreateOrderResponse(
        order_id=rz_order["id"],
        amount=amount,
        currency="INR",
        key_id=settings.RAZORPAY_KEY_ID,
        plan=body.plan,
        billing_cycle=body.billing_cycle,
        prefill_name=current_user.full_name or "",
        prefill_email=current_user.email,
    )


@router.post("/verify", response_model=UserProfile)
async def verify_payment(
    body: VerifyPaymentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfile:
    """
    Verify payment signature (client-side callback).
    On success, activates the subscription and returns the updated user profile.
    """
    if not _verify_payment_signature(
        body.razorpay_order_id, body.razorpay_payment_id, body.razorpay_signature
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment signature verification failed.",
        )

    # Load the corresponding Payment record
    result = await db.execute(
        select(Payment).where(
            Payment.razorpay_order_id == body.razorpay_order_id,
            Payment.user_id == current_user.id,
        )
    )
    payment = result.scalar_one_or_none()
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment order not found.")

    if payment.status == PaymentStatus.captured:
        # Already processed — idempotent, just return current user
        return UserProfile.model_validate(current_user)

    # Mark payment captured
    payment.razorpay_payment_id = body.razorpay_payment_id
    payment.razorpay_signature = body.razorpay_signature
    payment.status = PaymentStatus.captured

    # Activate subscription
    await _activate_subscription(current_user, payment.plan, payment.billing_cycle, db)

    return UserProfile.model_validate(current_user)


@router.post("/webhook", status_code=200)
async def razorpay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_razorpay_signature: str | None = Header(default=None),
) -> dict[str, str]:
    """
    Razorpay webhook receiver.
    Handles payment.captured and payment.failed events.
    Signature is verified against RAZORPAY_WEBHOOK_SECRET.
    """
    raw_body = await request.body()

    # Signature verification
    if not x_razorpay_signature:
        raise HTTPException(status_code=400, detail="Missing signature header.")
    if not _verify_webhook_signature(raw_body, x_razorpay_signature):
        raise HTTPException(status_code=400, detail="Invalid webhook signature.")

    import json
    try:
        event: dict[str, Any] = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body.")

    event_type: str = event.get("event", "")
    payload = event.get("payload", {})

    if event_type == "payment.captured":
        rz_payment = payload.get("payment", {}).get("entity", {})
        order_id: str = rz_payment.get("order_id", "")
        payment_id_str: str = rz_payment.get("id", "")
        await _handle_payment_captured(order_id, payment_id_str, db)

    elif event_type == "payment.failed":
        rz_payment = payload.get("payment", {}).get("entity", {})
        order_id = rz_payment.get("order_id", "")
        await _handle_payment_failed(order_id, db)

    return {"status": "ok"}


async def _handle_payment_captured(
    order_id: str, razorpay_payment_id: str, db: AsyncSession
) -> None:
    """Idempotent: activate subscription when webhook confirms capture."""
    if not order_id:
        return

    result = await db.execute(
        select(Payment).where(Payment.razorpay_order_id == order_id)
    )
    payment = result.scalar_one_or_none()
    if payment is None or payment.status == PaymentStatus.captured:
        return  # Not found or already processed

    payment.razorpay_payment_id = razorpay_payment_id
    payment.status = PaymentStatus.captured

    # Load the user
    user_result = await db.execute(
        select(User).where(User.id == payment.user_id)
    )
    user = user_result.scalar_one_or_none()
    if user is None:
        await db.commit()
        return

    await _activate_subscription(user, payment.plan, payment.billing_cycle.value, db)


async def _handle_payment_failed(order_id: str, db: AsyncSession) -> None:
    if not order_id:
        return
    result = await db.execute(
        select(Payment).where(Payment.razorpay_order_id == order_id)
    )
    payment = result.scalar_one_or_none()
    if payment and payment.status == PaymentStatus.created:
        payment.status = PaymentStatus.failed
        await db.commit()


@router.get("/history", response_model=list[PaymentRecord])
async def payment_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Payment]:
    """Return payment history for the authenticated user, newest first."""
    result = await db.execute(
        select(Payment)
        .where(Payment.user_id == current_user.id)
        .order_by(Payment.created_at.desc())
        .limit(50)
    )
    return list(result.scalars().all())

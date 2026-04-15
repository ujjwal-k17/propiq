"""Payment Pydantic schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


# ── Request bodies ────────────────────────────────────────────────────────────

class CreateOrderRequest(BaseModel):
    plan: Literal["basic", "pro"]
    billing_cycle: Literal["monthly", "annual"]


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


# ── Response bodies ───────────────────────────────────────────────────────────

class CreateOrderResponse(BaseModel):
    order_id: str
    amount: int          # paise
    currency: str
    key_id: str
    plan: str
    billing_cycle: str
    prefill_name: str
    prefill_email: str


class PaymentRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    plan: str
    billing_cycle: str
    amount_paise: int
    currency: str
    status: str
    razorpay_order_id: str
    razorpay_payment_id: str | None = None
    created_at: datetime

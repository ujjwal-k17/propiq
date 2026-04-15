"""
Auth routes
===========
POST /auth/register      — create account
POST /auth/login         — JWT login (OAuth2 password flow)
GET  /auth/me            — current user profile
PUT  /auth/me            — update profile fields
POST /auth/watchlist/{project_id}   — add to watchlist
DELETE /auth/watchlist/{project_id} — remove from watchlist
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.project import Project
from app.models.user import RiskAppetite, User
from app.schemas.user import Token, TokenPayload, UserCreate, UserProfile, UserUpdate

router = APIRouter(prefix="/auth")

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login"
)
# Optional variant — does not raise 401 when token absent
oauth2_optional = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login",
    auto_error=False,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)


def _hash_password(plain: str) -> str:
    return _pwd.hash(plain)


def _create_token(user_id: uuid.UUID) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    return jwt.encode(
        {"sub": str(user_id), "exp": expire},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


# ── Auth dependencies ─────────────────────────────────────────────────────────

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Raise 401 if token is missing or invalid."""
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id: str | None = payload.get("sub")
        if not user_id:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exc
    return user


async def get_optional_current_user(
    token: str | None = Depends(oauth2_optional),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Return User if valid token present, else None. Never raises."""
    if not token:
        return None
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id: str | None = payload.get("sub")
        if not user_id:
            return None
        result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
        user = result.scalar_one_or_none()
        return user if (user and user.is_active) else None
    except Exception:
        return None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=Token,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new PropIQ account",
)
async def register(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    # Duplicate email check
    existing = (
        await db.execute(select(User).where(User.email == payload.email))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user = User(
        email=payload.email,
        hashed_password=_hash_password(payload.password),
        full_name=payload.full_name,
        is_nri=payload.is_nri,
        preferred_cities=payload.preferred_cities or [],
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    return {
        "access_token": _create_token(user.id),
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": UserProfile.model_validate(user),
    }


@router.post(
    "/login",
    response_model=Token,
    summary="Login with email and password (OAuth2 password flow)",
)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(select(User).where(User.email == form.username))
    user = result.scalar_one_or_none()

    if not user or not _verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated",
        )

    return {
        "access_token": _create_token(user.id),
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": UserProfile.model_validate(user),
    }


@router.get(
    "/me",
    response_model=UserProfile,
    summary="Get current user profile",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> User:
    return current_user


@router.put(
    "/me",
    response_model=UserProfile,
    summary="Update profile fields",
)
async def update_me(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    update_data = payload.model_dump(exclude_none=True)

    # Validate risk_appetite value if provided
    if "risk_appetite" in update_data:
        try:
            update_data["risk_appetite"] = RiskAppetite(update_data["risk_appetite"])
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"risk_appetite must be one of: {[e.value for e in RiskAppetite]}",
            )

    for field, value in update_data.items():
        setattr(current_user, field, value)

    await db.flush()
    await db.refresh(current_user)
    return current_user


@router.post(
    "/watchlist/{project_id}",
    response_model=dict,
    summary="Add a project to watchlist",
)
async def add_to_watchlist(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    # Verify project exists
    project = (
        await db.execute(select(Project).where(Project.id == project_id))
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    pid_str = str(project_id)
    watchlist: list = list(current_user.watchlist_project_ids or [])
    if pid_str not in watchlist:
        watchlist.append(pid_str)
        current_user.watchlist_project_ids = watchlist
        await db.flush()

    return {"watchlist": current_user.watchlist_project_ids}


@router.delete(
    "/watchlist/{project_id}",
    response_model=dict,
    summary="Remove a project from watchlist",
)
async def remove_from_watchlist(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    pid_str = str(project_id)
    watchlist: list = list(current_user.watchlist_project_ids or [])
    if pid_str in watchlist:
        watchlist.remove(pid_str)
        current_user.watchlist_project_ids = watchlist
        await db.flush()

    return {"watchlist": current_user.watchlist_project_ids}

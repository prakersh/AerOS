from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel, EmailStr
from sqlmodel import Session

from aeros.config import settings
from aeros.db import get_session
from aeros.models.user import UserStatus
from aeros.security.auth_context import AuthContext, get_current_user
from aeros.security.jwt import create_access_token, create_refresh_token, decode_token
from aeros.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: str
    role: str = "buyer"

    def __init__(self, **data: object) -> None:
        super().__init__(**data)
        if len(self.password) < 8:
            raise ValueError("Password must be at least 8 characters")


class UserResponse(BaseModel):
    id: int
    email: str
    role: str
    display_name: str
    org_id: int | None


def _set_auth_cookies(response: Response, access: str, refresh: str) -> None:
    secure = not settings.debug
    response.set_cookie(
        "access_token", access, httponly=True, samesite="lax", max_age=15 * 60, secure=secure
    )
    response.set_cookie(
        "refresh_token", refresh, httponly=True, samesite="lax", max_age=7 * 86400, secure=secure
    )


@router.post("/login")
def login(body: LoginRequest, response: Response, session: Session = Depends(get_session)):
    user = auth_service.authenticate(session, body.email, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access = create_access_token(user.id, user.role.value)  # type: ignore[arg-type]
    refresh = create_refresh_token(user.id)  # type: ignore[arg-type]

    _set_auth_cookies(response, access, refresh)
    return UserResponse(
        id=user.id,  # type: ignore[arg-type]
        email=user.email,
        role=user.role.value,
        display_name=user.display_name,
        org_id=user.org_id,
    )


@router.post("/register")
def register(body: RegisterRequest, response: Response, session: Session = Depends(get_session)):
    if body.role not in ("buyer", "vendor"):
        raise HTTPException(status_code=400, detail="Invalid role")
    try:
        user = auth_service.register_user(
            session, body.email, body.password, body.display_name, body.role
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e

    access = create_access_token(user.id, user.role.value)  # type: ignore[arg-type]
    refresh = create_refresh_token(user.id)  # type: ignore[arg-type]

    _set_auth_cookies(response, access, refresh)
    return UserResponse(
        id=user.id,  # type: ignore[arg-type]
        email=user.email,
        role=user.role.value,
        display_name=user.display_name,
        org_id=user.org_id,
    )


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"ok": True}


@router.get("/me")
def me(
    current_user: AuthContext = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    user = auth_service.get_user_by_id(session, current_user.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(
        id=user.id,  # type: ignore[arg-type]
        email=user.email,
        role=user.role.value,
        display_name=user.display_name,
        org_id=user.org_id,
    )


@router.get("/demo-accounts")
def demo_accounts():
    if not settings.show_demo_credentials:
        raise HTTPException(status_code=404, detail="Demo credentials disabled")

    def _acct(role, email, pw, label):
        return {"role": role, "email": email, "password": pw, "label": label}

    return [
        _acct("Buyer", "buyer@aeros.demo", "buyer123", "Buyer"),
        _acct("Vendor", "freshfarm@vendor.demo", "vendor123", "FreshFarm Dairy"),
        _acct("Vendor", "sabzi@vendor.demo", "vendor123", "Sabzi Mandi Co"),
        _acct("Vendor", "bakery@vendor.demo", "vendor123", "Bakery Bros"),
        _acct("Vendor", "metro@vendor.demo", "vendor123", "Metro FMCG Supply"),
        _acct("Vendor", "kirana@vendor.demo", "vendor123", "Kirana King"),
        _acct("Vendor", "greenvalley@vendor.demo", "vendor123", "Green Valley Produce"),
        _acct("Vendor", "daily@vendor.demo", "vendor123", "Daily Beverages"),
        _acct("Vendor", "annapurna@vendor.demo", "vendor123", "Annapurna Foods"),
        _acct("Admin", "admin@aeros.demo", "admin123", "Admin"),
    ]


@router.post("/refresh")
def refresh(
    response: Response,
    session: Session = Depends(get_session),
    refresh_token: str | None = Cookie(default=None),
):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = decode_token(refresh_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token") from None
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    user_id = int(payload["sub"])
    user = auth_service.get_user_by_id(session, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(status_code=403, detail="Account suspended")

    access = create_access_token(user_id, user.role.value)  # type: ignore[arg-type]
    new_refresh = create_refresh_token(user_id)
    _set_auth_cookies(response, access, new_refresh)
    return {"ok": True}

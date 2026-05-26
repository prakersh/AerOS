from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, EmailStr
from sqlmodel import Session

from aeros.db import get_session
from aeros.models.user import Role
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


class UserResponse(BaseModel):
    id: int
    email: str
    role: str
    display_name: str
    org_id: int | None


@router.post("/login")
def login(body: LoginRequest, response: Response, session: Session = Depends(get_session)):
    user = auth_service.authenticate(session, body.email, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access = create_access_token(user.id, user.role.value)  # type: ignore[arg-type]
    refresh = create_refresh_token(user.id)  # type: ignore[arg-type]

    response.set_cookie(
        "access_token", access, httponly=True, samesite="lax", max_age=15 * 60
    )
    response.set_cookie(
        "refresh_token", refresh, httponly=True, samesite="lax", max_age=7 * 86400
    )
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
        raise HTTPException(status_code=409, detail=str(e))

    access = create_access_token(user.id, user.role.value)  # type: ignore[arg-type]
    refresh = create_refresh_token(user.id)  # type: ignore[arg-type]

    response.set_cookie(
        "access_token", access, httponly=True, samesite="lax", max_age=15 * 60
    )
    response.set_cookie(
        "refresh_token", refresh, httponly=True, samesite="lax", max_age=7 * 86400
    )
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
def me(current_user: AuthContext = Depends(get_current_user), session: Session = Depends(get_session)):
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


@router.post("/refresh")
def refresh(response: Response, refresh_token: str | None = None):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = decode_token(refresh_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    user_id = int(payload["sub"])
    access = create_access_token(user_id, payload.get("role", "buyer"))
    response.set_cookie(
        "access_token", access, httponly=True, samesite="lax", max_age=15 * 60
    )
    return {"ok": True}

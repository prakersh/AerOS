from dataclasses import dataclass

from fastapi import Cookie, Depends, HTTPException
from sqlmodel import Session

from aeros.db import get_session
from aeros.models.user import Role, User
from aeros.security.jwt import decode_token


@dataclass
class AuthContext:
    user_id: int
    role: Role
    org_id: int | None = None


def get_current_user(
    access_token: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
) -> AuthContext:
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_token(access_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token") from None
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")

    user_id = int(payload["sub"])
    user = session.get(User, user_id)
    org_id = user.org_id if user else None

    return AuthContext(
        user_id=user_id,
        role=Role(payload["role"]),
        org_id=org_id,
    )


def require_role(*roles: Role):
    def dependency(current_user: AuthContext = Depends(get_current_user)) -> AuthContext:
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user

    return Depends(dependency)

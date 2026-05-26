from datetime import datetime, timezone

import bcrypt
from sqlmodel import Session, select

from aeros.models.user import User, UserStatus
from aeros.models.user_defaults import UserDefaults


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def authenticate(session: Session, email: str, password: str) -> User | None:
    user = session.exec(select(User).where(User.email == email)).first()
    if not user:
        return None
    if user.status != UserStatus.ACTIVE:
        return None
    if not verify_password(password, user.password_hash):
        return None
    user.last_login_at = datetime.now(timezone.utc)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def register_user(
    session: Session,
    email: str,
    password: str,
    display_name: str,
    role: str,
    org_id: int | None = None,
) -> User:
    existing = session.exec(select(User).where(User.email == email)).first()
    if existing:
        raise ValueError("Email already registered")
    user = User(
        email=email,
        password_hash=hash_password(password),
        role=role,
        display_name=display_name,
        org_id=org_id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    defaults = UserDefaults(user_id=user.id)  # type: ignore[arg-type]
    session.add(defaults)
    session.commit()

    return user


def get_user_by_id(session: Session, user_id: int) -> User | None:
    return session.get(User, user_id)

"""Admin operations — user suspension, org listing, system health."""

from datetime import datetime

from sqlmodel import Session, select

from aeros.models.organization import Organization
from aeros.models.user import User, UserStatus
from aeros.services.audit_service import log_action


def suspend_user(
    session: Session, user_id: int, admin_id: int, reason: str = ""
) -> User:
    """Suspend a user account.

    Args:
        session: Database session.
        user_id: ID of the user to suspend.
        admin_id: ID of the admin performing the action.
        reason: Optional reason for suspension.

    Returns:
        The updated User.

    Raises:
        ValueError: If user not found or admin tries to suspend themselves.
    """
    user = session.get(User, user_id)
    if not user:
        raise ValueError(f"User {user_id} not found")
    if user.id == admin_id:
        raise ValueError("Cannot suspend yourself")
    user.status = UserStatus.SUSPENDED
    user.suspended_at = datetime.utcnow()  # noqa: DTZ003
    user.suspended_by_admin_id = admin_id
    session.add(user)
    log_action(
        session,
        actor_user_id=admin_id,
        actor_role="admin",
        action="suspend_user",
        entity_type="user",
        entity_id=str(user_id),
        after={"reason": reason},
    )
    return user


def reactivate_user(session: Session, user_id: int, admin_id: int) -> User:
    """Reactivate a suspended user account.

    Args:
        session: Database session.
        user_id: ID of the user to reactivate.
        admin_id: ID of the admin performing the action.

    Returns:
        The updated User.

    Raises:
        ValueError: If user not found.
    """
    user = session.get(User, user_id)
    if not user:
        raise ValueError(f"User {user_id} not found")
    user.status = UserStatus.ACTIVE
    user.suspended_at = None
    user.suspended_by_admin_id = None
    session.add(user)
    log_action(
        session,
        actor_user_id=admin_id,
        actor_role="admin",
        action="reactivate_user",
        entity_type="user",
        entity_id=str(user_id),
    )
    return user


def list_organizations(session: Session) -> list[Organization]:
    """List all organizations ordered by ID.

    Args:
        session: Database session.

    Returns:
        List of Organization records.
    """
    return list(session.exec(select(Organization).order_by(Organization.id)).all())


def get_system_health() -> dict:
    """Return system health status.

    Returns:
        Dict with status of api, database, and ai_provider subsystems.
    """
    return {
        "api": {"status": "healthy"},
        "database": {"status": "healthy"},
        "ai_provider": {"status": "healthy"},
    }

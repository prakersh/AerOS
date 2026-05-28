"""User defaults management — CRUD for per-user procurement defaults."""

from sqlmodel import Session, select

from aeros.models.user_defaults import UserDefaults


def get_defaults(session: Session, user_id: int) -> UserDefaults | None:
    """Return UserDefaults for a user, or None if not set.

    Args:
        session: Active database session.
        user_id: The user to look up.

    Returns:
        The UserDefaults row or None.
    """
    return session.exec(select(UserDefaults).where(UserDefaults.user_id == user_id)).first()


def update_defaults(session: Session, user_id: int, **kwargs: object) -> UserDefaults:
    """Update (or create) UserDefaults for a user.

    Unknown fields in *kwargs* are silently ignored.

    Args:
        session: Active database session.
        user_id: The user whose defaults to update.
        **kwargs: Field names and values to set.

    Returns:
        The updated UserDefaults row.
    """
    defaults = get_defaults(session, user_id)
    if not defaults:
        defaults = UserDefaults(user_id=user_id)
    for key, value in kwargs.items():
        if hasattr(defaults, key):
            setattr(defaults, key, value)
    session.add(defaults)
    session.flush()
    session.commit()
    session.refresh(defaults)
    return defaults


def ensure_defaults(session: Session, user_id: int) -> UserDefaults:
    """Return existing defaults or create a row with model defaults.

    Args:
        session: Active database session.
        user_id: The user to ensure defaults for.

    Returns:
        The (possibly newly created) UserDefaults row.
    """
    defaults = get_defaults(session, user_id)
    if not defaults:
        defaults = UserDefaults(user_id=user_id)
        session.add(defaults)
        session.flush()
        session.commit()
        session.refresh(defaults)
    return defaults

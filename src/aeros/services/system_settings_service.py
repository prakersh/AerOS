"""System settings management with DB storage and defaults fallback."""

from datetime import datetime
from typing import Any

from sqlmodel import Session, select

DEFAULT_SETTINGS: dict[str, dict[str, str]] = {
    "max_upload_size_mb": {
        "value": "25",
        "type": "int",
        "description": "Max upload file size in MB",
    },
    "rate_limit_rpm": {
        "value": "60",
        "type": "int",
        "description": "API rate limit per minute",
    },
    "ai_budget_per_rfx": {
        "value": "100000",
        "type": "int",
        "description": "Max AI tokens per RFx",
    },
    "ai_budget_per_user_day": {
        "value": "500000",
        "type": "int",
        "description": "Max AI tokens per user per day",
    },
    "telemetry_retention_days": {
        "value": "30",
        "type": "int",
        "description": "Days to keep telemetry data",
    },
    "session_timeout_minutes": {
        "value": "60",
        "type": "int",
        "description": "Session timeout in minutes",
    },
}


def get_setting(session: Session, key: str) -> str | None:
    """Get a single setting value by key.

    Checks DB first, falls back to DEFAULT_SETTINGS.

    Args:
        session: Database session.
        key: Setting key name.

    Returns:
        Setting value string, or None if key unknown.
    """
    try:
        from aeros.models.system_setting import SystemSetting

        setting = session.exec(select(SystemSetting).where(SystemSetting.key == key)).first()
        if setting:
            return setting.value
    except Exception:  # noqa: S110
        pass
    default = DEFAULT_SETTINGS.get(key)
    return default["value"] if default else None


def get_all_settings(session: Session) -> list[dict[str, Any]]:
    """Get all settings, merging DB values with defaults.

    Args:
        session: Database session.

    Returns:
        List of setting dicts with key, value, type, description, source.
    """
    result: list[dict[str, Any]] = []
    try:
        from aeros.models.system_setting import SystemSetting

        db_settings = {s.key: s for s in session.exec(select(SystemSetting)).all()}
    except Exception:
        db_settings: dict[str, Any] = {}  # type: ignore[no-redef]

    for key, default in DEFAULT_SETTINGS.items():
        db = db_settings.get(key)
        result.append(
            {
                "key": key,
                "value": db.value if db else default["value"],
                "type": default["type"],
                "description": default["description"],
                "source": "database" if db else "default",
            }
        )
    return result


def update_setting(session: Session, key: str, value: str, user_id: int) -> dict[str, Any]:
    """Update a setting value.

    Attempts DB storage; falls back to memory-only response if model unavailable.

    Args:
        session: Database session.
        key: Setting key name.
        value: New value string.
        user_id: ID of user making the change.

    Returns:
        Dict with key, value, and source.
    """
    try:
        from aeros.models.system_setting import SystemSetting

        setting = session.exec(select(SystemSetting).where(SystemSetting.key == key)).first()
        if setting:
            setting.value = value
            setting.updated_by_user_id = user_id
            setting.updated_at = datetime.utcnow()  # noqa: DTZ003
        else:
            default = DEFAULT_SETTINGS.get(key, {})
            setting = SystemSetting(
                key=key,
                value=value,
                value_type=default.get("type", "string"),
                description=default.get("description", ""),
                updated_by_user_id=user_id,
            )
        session.add(setting)
        session.flush()
        session.commit()
        session.refresh(setting)
        return {"key": key, "value": value, "source": "database"}
    except Exception:
        return {
            "key": key,
            "value": value,
            "source": "memory",
            "error": "SystemSetting model not available",
        }

import json

from sqlmodel import Session

from aeros.models.audit import AuditLog


def log_action(
    session: Session,
    *,
    actor_user_id: int | None,
    actor_role: str | None,
    action: str,
    entity_type: str,
    entity_id: str,
    before: dict | None = None,
    after: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_json=json.dumps(before) if before else None,
        after_json=json.dumps(after) if after else None,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry

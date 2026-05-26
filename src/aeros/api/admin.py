import json

from fastapi import APIRouter, Depends
from sqlmodel import Session, select, func

from aeros.db import get_session
from aeros.models.user import Role, User
from aeros.models.audit import AuditLog
from aeros.models.rfx import RFxRun, Attachment
from aeros.models.vendor import Vendor
from aeros.models.offer import Offer
from aeros.security.auth_context import AuthContext, require_role

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/stats")
def get_stats(
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.ADMIN),
):
    total_users = session.exec(select(func.count(User.id))).one()
    total_rfx = session.exec(select(func.count(RFxRun.id))).one()
    total_vendors = session.exec(select(func.count(Vendor.id))).one()
    total_offers = session.exec(select(func.count(Offer.id))).one()
    total_extractions = session.exec(select(func.count(Attachment.id))).one()

    return {
        "total_users": total_users,
        "total_rfx": total_rfx,
        "total_vendors": total_vendors,
        "total_offers": total_offers,
        "total_extractions": total_extractions,
    }


@router.get("/users")
def list_users(
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.ADMIN),
):
    users = list(session.exec(select(User).order_by(User.id)).all())
    return [
        {
            "id": u.id,
            "email": u.email,
            "display_name": u.display_name,
            "role": u.role.value,
            "status": u.status.value,
            "created_at": u.created_at.isoformat() if u.created_at else "",
        }
        for u in users
    ]


@router.get("/audit")
def list_audit(
    limit: int = 100,
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.ADMIN),
):
    logs = list(
        session.exec(
            select(AuditLog)
            .order_by(AuditLog.created_at.desc())  # type: ignore[union-attr]
            .limit(limit)
        ).all()
    )
    results = []
    for log in logs:
        actor = session.get(User, log.actor_user_id) if log.actor_user_id else None
        after = {}
        if log.after_json:
            try:
                after = json.loads(log.after_json)
            except json.JSONDecodeError:
                pass
        results.append({
            "id": log.id,
            "actor_name": actor.display_name if actor else "System",
            "actor_role": log.actor_role,
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "details": after,
            "created_at": log.created_at.isoformat() if log.created_at else "",
        })
    return results

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, func, select

from aeros.db import get_session
from aeros.models.audit import AuditLog
from aeros.models.offer import Offer
from aeros.models.rfx import Attachment, RFxRun
from aeros.models.user import Role, User
from aeros.models.vendor import Vendor
from aeros.security.auth_context import AuthContext, require_role
from aeros.services import admin_service, ai_config_service, system_settings_service

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
    limit: int = Query(default=100, ge=1, le=500),
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


# ---------------------------------------------------------------------------
# User suspend / reactivate
# ---------------------------------------------------------------------------


class SuspendRequest(BaseModel):
    reason: str = ""


@router.post("/users/{user_id}/suspend")
def suspend_user(
    user_id: int,
    body: SuspendRequest,
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.ADMIN),
) -> dict:
    """Suspend a user account."""
    try:
        user = admin_service.suspend_user(
            session, user_id, caller.user_id, reason=body.reason
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {
        "id": user.id,
        "email": user.email,
        "status": user.status.value,
        "suspended_at": user.suspended_at.isoformat() if user.suspended_at else "",
    }


@router.post("/users/{user_id}/reactivate")
def reactivate_user(
    user_id: int,
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.ADMIN),
) -> dict:
    """Reactivate a suspended user account."""
    try:
        user = admin_service.reactivate_user(session, user_id, caller.user_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {
        "id": user.id,
        "email": user.email,
        "status": user.status.value,
    }


# ---------------------------------------------------------------------------
# Organizations
# ---------------------------------------------------------------------------


@router.get("/orgs")
def list_orgs(
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.ADMIN),
) -> list[dict]:
    """List all organizations."""
    orgs = admin_service.list_organizations(session)
    return [
        {
            "id": o.id,
            "name": o.name,
            "type": o.type.value,
            "created_at": o.created_at.isoformat() if o.created_at else "",
        }
        for o in orgs
    ]


# ---------------------------------------------------------------------------
# AI Providers
# ---------------------------------------------------------------------------


@router.get("/ai/providers")
def list_ai_providers(
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.ADMIN),
) -> list[dict]:
    """List configured AI providers."""
    return ai_config_service.list_providers(session)


class TestProviderRequest(BaseModel):
    provider_name: str


@router.post("/ai/providers/test")
def test_ai_provider(
    body: TestProviderRequest,
    caller: AuthContext = require_role(Role.ADMIN),
) -> dict:
    """Test connectivity to an AI provider."""
    return ai_config_service.test_provider_connection(body.provider_name)


# ---------------------------------------------------------------------------
# System Settings
# ---------------------------------------------------------------------------


@router.get("/settings")
def get_settings(
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.ADMIN),
) -> list[dict]:
    """Get all system settings."""
    return system_settings_service.get_all_settings(session)


class UpdateSettingRequest(BaseModel):
    value: str


@router.put("/settings/{key}")
def update_setting(
    key: str,
    body: UpdateSettingRequest,
    session: Session = Depends(get_session),
    caller: AuthContext = require_role(Role.ADMIN),
) -> dict:
    """Update a system setting."""
    return system_settings_service.update_setting(session, key, body.value, caller.user_id)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@router.get("/health")
def system_health(
    caller: AuthContext = require_role(Role.ADMIN),
) -> dict:
    """Get system health status."""
    return admin_service.get_system_health()

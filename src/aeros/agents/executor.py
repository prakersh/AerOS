"""Tool executor — maps tool calls to service-layer functions."""

import contextlib
import time
from typing import Any

import structlog
from sqlmodel import Session

from aeros.agents.tools import ToolResult
from aeros.security.auth_context import AuthContext

logger = structlog.get_logger()

TOOL_ALIASES = {
    "log": "daily_summary",
    "search": "search_inventory",
    "vendors": "list_vendors",
    "rfx": "list_rfx",
    "items": "search_inventory",
    "create": "create_rfx",
    "send": "dispatch_rfx",
    "compare": "evaluate_offers",
}


def execute_tool(
    tool_name: str,
    params: dict[str, Any],
    session: Session,
    caller: AuthContext,
) -> ToolResult:
    from aeros.agents.tools import TOOL_CATALOG

    tool_name = TOOL_ALIASES.get(tool_name, tool_name)
    t0 = time.monotonic()

    tool_def = TOOL_CATALOG.get(tool_name)
    if tool_def:
        role = caller.role.value if hasattr(caller.role, "value") else str(caller.role)
        if tool_def.buyer_only and role != "buyer":
            return ToolResult(
                tool=tool_name,
                success=False,
                message=f"Tool '{tool_name}' is not available for {role} role",
                latency_ms=0.0,
            )
        if tool_def.vendor_only and role != "vendor":
            return ToolResult(
                tool=tool_name,
                success=False,
                message=f"Tool '{tool_name}' is not available for {role} role",
                latency_ms=0.0,
            )

    try:
        data = _dispatch(tool_name, params, session, caller)
        latency = (time.monotonic() - t0) * 1000
        return ToolResult(
            tool=tool_name,
            success=True,
            data=data,
            latency_ms=latency,
        )
    except Exception as e:
        latency = (time.monotonic() - t0) * 1000
        logger.error("tool.exec.error", tool=tool_name, error=str(e))
        return ToolResult(
            tool=tool_name,
            success=False,
            message=str(e),
            latency_ms=latency,
        )


def _assert_rfx_owner(session: Session, rfx_id: int, user_id: int) -> None:
    """Buyer-side guard: the caller must own this RFx.

    The rfx_id reaching a tool is supplied by the LLM, which echoes
    user-controlled text — without this check a buyer could act on another
    org's RFx. Mirrors the REST layer's _verify_rfx_ownership.
    """
    from aeros.models.rfx import RFxRun

    rfx = session.get(RFxRun, rfx_id)
    if not rfx:
        raise ValueError(f"RFx #{rfx_id} not found")
    if rfx.buyer_id != user_id:
        raise PermissionError(f"Not authorized for RFx #{rfx_id}")


def _assert_vendor_invited(session: Session, rfx_id: int, user_id: int) -> int:
    """Vendor-side guard: the caller's vendor must be invited to this RFx.

    Returns the vendor id for convenience.
    """
    from sqlmodel import select

    from aeros.models.rfx import RFxVendor
    from aeros.models.vendor import Vendor

    vendor = session.exec(select(Vendor).where(Vendor.vendor_user_id == user_id)).first()
    if not vendor:
        raise ValueError("No vendor profile found")
    rv = session.exec(
        select(RFxVendor).where(RFxVendor.rfx_id == rfx_id, RFxVendor.vendor_id == vendor.id)
    ).first()
    if not rv:
        raise PermissionError(f"Not invited to RFx #{rfx_id}")
    assert vendor.id is not None
    return vendor.id


def _dispatch(name: str, params: dict[str, Any], session: Session, caller: AuthContext) -> Any:
    from aeros.services import (
        inventory_service,
        rfx_service,
        vendor_service,
    )

    org_id = caller.org_id or 0
    user_id = caller.user_id

    # ── Inventory ──
    if name == "search_inventory":
        return [
            {
                "id": s.id,
                "code": s.code,
                "name": s.name,
                "unit": s.unit,
                "last_price": s.last_price,
            }
            for s in inventory_service.search_skus(session, org_id, params["query"])
        ]

    if name == "list_categories":
        return inventory_service.list_categories(session)

    # ── RFx ──
    if name == "create_rfx":
        from datetime import datetime

        deadline = None
        if params.get("response_deadline"):
            with contextlib.suppress(ValueError, TypeError):
                deadline = datetime.fromisoformat(params["response_deadline"])
        rfx = rfx_service.create_rfx(
            session,
            buyer_id=user_id,
            title=params["title"],
            response_deadline=deadline,
            payment_terms_for_this_rfx=params.get("payment_terms", "NET30"),
            delivery_terms_for_this_rfx=params.get("delivery_terms", "doorstep"),
            currency_for_this_rfx=params.get("currency", "INR"),
            notes_for_vendors=params.get("notes_for_vendors"),
        )
        return {"rfx_id": rfx.id, "title": rfx.title, "status": "drafting"}

    if name == "add_line_items":
        _assert_rfx_owner(session, params["rfx_id"], user_id)
        ready: list[dict[str, Any]] = []
        needs_clarification: list[dict[str, Any]] = []
        not_found: list[Any] = []
        for item in params["items"]:
            ref = item.get("sku_id")
            if ref is None:
                raise ValueError("Each line item requires a sku_id")
            match, candidates = inventory_service.resolve_sku_ref(session, org_id, ref)
            if match:
                # Normalise to the real primary key so persistence is exact.
                ready.append({**item, "sku_id": match.id})
            elif candidates:
                needs_clarification.append(
                    {
                        "ref": ref,
                        "qty": item.get("qty"),
                        "unit_override": item.get("unit_override"),
                        "candidates": [
                            {
                                "id": s.id,
                                "code": s.code,
                                "name": s.name,
                                "unit": s.unit,
                                "last_price": s.last_price,
                            }
                            for s in candidates
                        ],
                    }
                )
            else:
                not_found.append(ref)

        added = (
            rfx_service.add_line_items(session, params["rfx_id"], ready) if ready else []
        )
        return {
            "rfx_id": params["rfx_id"],
            "count": len(added),
            "needs_clarification": needs_clarification,
            "not_found": not_found,
        }

    if name == "list_rfx":
        return rfx_service.list_rfx_for_buyer(session, user_id)

    if name == "get_rfx_details":
        _assert_rfx_owner(session, params["rfx_id"], user_id)
        details = rfx_service.get_rfx_with_details(session, params["rfx_id"])
        if not details:
            raise ValueError(f"RFx #{params['rfx_id']} not found")
        return details

    if name == "cancel_rfx":
        _assert_rfx_owner(session, params["rfx_id"], user_id)
        rfx = rfx_service.cancel_rfx(session, params["rfx_id"], user_id, params.get("reason", ""))
        return {"rfx_id": rfx.id, "status": "cancelled"}

    # ── Vendors ──
    if name == "list_vendors":
        vendors = vendor_service.list_vendors(session, org_id)
        return [
            {
                "id": v.id,
                "name": v.name,
                "email": v.primary_email,
                "categories": v.category_ids_csv,
                "score": v.performance_score,
                "has_telegram": bool(v.telegram_chat_id),
                "has_portal": bool(v.vendor_user_id),
            }
            for v in vendors
        ]

    if name == "get_vendor_suggestions":
        _assert_rfx_owner(session, params["rfx_id"], user_id)
        return rfx_service.get_vendor_suggestions(session, params["rfx_id"], org_id)

    # ── Dispatch ──
    if name == "invite_vendor":
        from aeros.channels.correlation import generate_correlation_token

        _assert_rfx_owner(session, params["rfx_id"], user_id)
        _, token_hash = generate_correlation_token(params["rfx_id"], params["vendor_id"])
        rv = rfx_service.invite_vendor(session, params["rfx_id"], params["vendor_id"], token_hash)
        return {"invited": True, "vendor_id": params["vendor_id"], "status": rv.status.value}

    if name == "dispatch_rfx":
        from sqlmodel import select

        from aeros.channels.correlation import generate_correlation_token
        from aeros.models.rfx import RFxVendor

        rfx_id = params["rfx_id"]
        _assert_rfx_owner(session, rfx_id, user_id)

        # A freshly drafted RFx has no vendors invited yet. Auto-invite the
        # category-matched vendors so "send it to vendors" actually reaches
        # inboxes instead of dispatching to nobody.
        already = session.exec(select(RFxVendor).where(RFxVendor.rfx_id == rfx_id)).first()
        invited_names: list[str] = []
        if not already:
            suggestions = rfx_service.get_vendor_suggestions(session, rfx_id, org_id).get(
                "suggestions", []
            )
            for s in suggestions[:5]:
                line_ids = [mi["line_item_id"] for mi in s.get("matching_items", [])]
                _, token_hash = generate_correlation_token(rfx_id, s["vendor_id"])
                rfx_service.invite_vendor(session, rfx_id, s["vendor_id"], token_hash, line_ids)
                invited_names.append(s.get("vendor_name", f"Vendor #{s['vendor_id']}"))

        rfx = rfx_service.dispatch_rfx(session, rfx_id, user_id)
        return {
            "rfx_id": rfx.id,
            "status": rfx.status.value,
            "vendors": invited_names,
            "vendor_count": len(invited_names),
        }

    # ── Evaluation ──
    if name == "evaluate_offers":
        _assert_rfx_owner(session, params["rfx_id"], user_id)
        details = rfx_service.get_rfx_with_details(session, params["rfx_id"])
        if not details:
            raise ValueError(f"RFx #{params['rfx_id']} not found")
        offers = details.get("vendor_offers", [])
        quoted = [o for o in offers if o.get("status") == "quoted"]
        return {
            "rfx_id": params["rfx_id"],
            "total_vendors": len(offers),
            "quoted": len(quoted),
            "offers": quoted,
            "line_items": details.get("line_items", []),
        }

    # ── Award ──
    if name == "award_rfx":
        _assert_rfx_owner(session, params["rfx_id"], user_id)
        rfx = rfx_service.award_rfx(session, params["rfx_id"], user_id, params["decisions"])
        return {"rfx_id": rfx.id, "status": "awarded"}

    # ── Vendor-side ──
    if name == "view_rfx_thread":
        _assert_vendor_invited(session, params["rfx_id"], user_id)
        details = rfx_service.get_rfx_with_details(session, params["rfx_id"])
        if not details:
            raise ValueError(f"RFx #{params['rfx_id']} not found")
        return {
            "title": details["title"],
            "status": details["status"],
            "line_items": details.get("line_items", []),
            "deadline": details.get("deadline"),
        }

    if name == "submit_quote":
        from sqlmodel import select

        from aeros.models.rfx import Message, RFxVendor, RFxVendorStatus, Thread
        from aeros.models.vendor import Vendor
        from aeros.services import offer_service

        vendor = session.exec(select(Vendor).where(Vendor.vendor_user_id == user_id)).first()
        if not vendor:
            raise ValueError("No vendor profile found")
        assert vendor.id is not None

        extraction_data = {
            "line_items": [
                {
                    "line_item_id": li.get("line_item_id"),
                    "unit_price": li.get("unit_price"),
                    "lead_time_days": li.get("lead_time_days"),
                    "confidence": 1.0,
                }
                for li in params.get("line_items", [])
            ],
            "payment_terms": params.get("payment_terms"),
            "delivery_terms": params.get("delivery_terms"),
            "vendor_remarks": params.get("vendor_remarks"),
            "confidence_overall": 1.0,
        }

        thread = session.exec(
            select(Thread).where(
                Thread.rfx_id == params["rfx_id"],
                Thread.vendor_id == vendor.id,
            )
        ).first()
        if not thread:
            raise ValueError("No thread found for this RFx — vendor may not be invited")

        msg = Message(
            thread_id=thread.id,
            sender_user_id=user_id,
            sender_kind="vendor",
            channel="in_app",
            body_text="Structured quote submitted via chat",
        )
        session.add(msg)
        session.commit()
        session.refresh(msg)
        assert msg.id is not None

        offer = offer_service.create_offer_from_extraction(
            session=session,
            rfx_id=params["rfx_id"],
            vendor_id=vendor.id,
            extraction_data=extraction_data,
            source_message_ids=[msg.id],
        )

        rv_record = session.exec(
            select(RFxVendor).where(
                RFxVendor.rfx_id == params["rfx_id"],
                RFxVendor.vendor_id == vendor.id,
            )
        ).first()
        if rv_record:
            rv_record.status = RFxVendorStatus.QUOTED
            session.add(rv_record)
            session.commit()

        return {"offer_id": offer.id, "revision": offer.revision_no}

    if name == "decline_rfx":
        from sqlmodel import select

        from aeros.models.vendor import Vendor

        vendor = session.exec(select(Vendor).where(Vendor.vendor_user_id == user_id)).first()
        if not vendor:
            raise ValueError("No vendor profile found")
        assert vendor.id is not None
        rv = rfx_service.decline_rfx_vendor(session, params["rfx_id"], vendor.id, params["reason"])
        return {"status": rv.status.value}

    # ── Analytics ──
    if name == "daily_summary":
        rfx_list = rfx_service.list_rfx_for_buyer(session, user_id)
        drafting = sum(1 for r in rfx_list if r.get("status") == "drafting")
        dispatched = sum(1 for r in rfx_list if r.get("status") == "dispatched")
        awarded = sum(1 for r in rfx_list if r.get("status") == "awarded")
        return {
            "total_rfx": len(rfx_list),
            "drafting": drafting,
            "dispatched": dispatched,
            "awarded": awarded,
        }

    if name == "clear_context":
        return {"cleared": True}

    raise ValueError(f"Unknown tool: {name}")

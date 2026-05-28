"""Background worker for offer extraction from uploaded documents."""

import traceback

import structlog
from sqlmodel import Session, select

from aeros.db import engine
from aeros.models.rfx import (
    Attachment,
    ExtractionStatus,
    RFxVendor,
    RFxVendorStatus,
)
from aeros.services import offer_service

logger = structlog.get_logger()


async def extract_offer_from_attachment(
    attachment_id: int,
    rfx_id: int,
    vendor_id: int,
    message_id: int,
    session: Session | None = None,
) -> bool:
    """Extract a structured offer from an attachment using the EvaluationAgent.

    Args:
        attachment_id: ID of the Attachment record.
        rfx_id: Associated RFx ID.
        vendor_id: Associated Vendor ID.
        message_id: Source Message ID.
        session: Optional caller session. Request-path callers (uploads,
            Telegram webhook) pass their own session so the attachment is
            visible; the Huey worker omits it and opens its own.

    Returns:
        True if extraction succeeded, False otherwise.
    """
    if session is not None:
        return await _extract(session, attachment_id, rfx_id, vendor_id, message_id)
    with Session(engine) as own_session:
        return await _extract(own_session, attachment_id, rfx_id, vendor_id, message_id)


async def _extract(
    session: Session,
    attachment_id: int,
    rfx_id: int,
    vendor_id: int,
    message_id: int,
) -> bool:
    from aeros.agents.base import AgentContext
    from aeros.agents.evaluation import EvaluationAgent
    from aeros.ai.factory import get_chat_provider, get_vision_provider
    from aeros.models.user import Role
    from aeros.security.auth_context import AuthContext

    attachment = session.get(Attachment, attachment_id)
    if not attachment:
        logger.error("extract.attachment_not_found", id=attachment_id)
        return False

    attachment.extraction_status = ExtractionStatus.PENDING
    attachment.extraction_attempts += 1
    session.add(attachment)
    session.commit()

    try:
        caller = AuthContext(user_id=0, org_id=0, role=Role.ADMIN)
        agent = EvaluationAgent()
        ctx = AgentContext(
            session=session,
            caller=caller,
            chat_provider=get_chat_provider(),
            vision_provider=get_vision_provider(),
        )
        result = await agent.run(ctx, str(message_id))

        if result.success and result.data:
            offer_service.create_offer_from_extraction(
                session=session,
                rfx_id=rfx_id,
                vendor_id=vendor_id,
                extraction_data=result.data,
                source_message_ids=[message_id],
            )
            attachment.extraction_status = ExtractionStatus.EXTRACTED
            session.add(attachment)

            rv = session.exec(
                select(RFxVendor).where(
                    RFxVendor.rfx_id == rfx_id,
                    RFxVendor.vendor_id == vendor_id,
                )
            ).first()
            if rv:
                rv.status = RFxVendorStatus.QUOTED
                session.add(rv)

            session.commit()
            logger.info("extract.success", rfx_id=rfx_id, vendor_id=vendor_id)
            return True
        else:
            attachment.extraction_status = ExtractionStatus.FAILED
            session.add(attachment)
            session.commit()
            return False

    except Exception as e:
        logger.error(
            "extract.failed",
            error=str(e),
            traceback=traceback.format_exc(),
        )
        attachment.extraction_status = ExtractionStatus.FAILED
        session.add(attachment)
        session.commit()
        return False

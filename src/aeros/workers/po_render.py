"""Background worker for PO PDF rendering and dispatch."""

import structlog
from sqlmodel import Session

from aeros.db import engine

logger = structlog.get_logger()


async def render_and_send_po(
    rfx_id: int,
    award_decisions: list[dict],
) -> bool:
    """Render Purchase Order PDFs and send them to awarded vendors.

    Args:
        rfx_id: The RFx ID for which POs are being generated.
        award_decisions: List of award decision dicts with vendor_id, etc.

    Returns:
        True if all POs were generated successfully, False otherwise.
    """
    from aeros.agents.base import AgentContext
    from aeros.agents.po import POAgent
    from aeros.ai.factory import get_chat_provider
    from aeros.security.auth_context import AuthContext

    with Session(engine) as session:
        try:
            caller = AuthContext(user_id=0, org_id=0, role="system")
            agent = POAgent()
            ctx = AgentContext(
                session=session,
                caller=caller,
                chat_provider=get_chat_provider(),
                rfx_id=rfx_id,
                metadata={"award_decisions": award_decisions},
            )
            result = await agent.run(ctx, "generate")
            if result.success:
                logger.info("po.render.success", rfx_id=rfx_id)
                return True
            else:
                logger.error("po.render.failed", rfx_id=rfx_id, message=result.message)
                return False
        except Exception as e:
            logger.error("po.render.error", rfx_id=rfx_id, error=str(e))
            return False

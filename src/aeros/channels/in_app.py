"""In-app message delivery channel — persists messages for the portal UI."""

import structlog
from sqlmodel import Session, select

from aeros.models.rfx import Thread, Message

logger = structlog.get_logger()


async def deliver_in_app(
    session: Session,
    thread_id: int,
    body_text: str,
    sender_kind: str = "system",
    sender_user_id: int | None = None,
    body_html: str | None = None,
) -> Message:
    """Create and persist an in-app message on the given thread.

    Args:
        session: Active database session.
        thread_id: Target thread ID.
        body_text: Plain text body.
        sender_kind: One of buyer/vendor/system/agent.
        sender_user_id: Optional user who sent the message.
        body_html: Optional HTML body.

    Returns:
        The persisted Message instance.
    """
    msg = Message(
        thread_id=thread_id,
        sender_user_id=sender_user_id,
        sender_kind=sender_kind,
        channel="in_app",
        body_text=body_text,
        body_html=body_html,
    )
    session.add(msg)
    session.commit()
    session.refresh(msg)
    logger.info("channel.in_app.delivered", thread_id=thread_id, message_id=msg.id)
    return msg


async def send_rfx_notification_in_app(
    session: Session,
    thread_id: int,
    rfx_title: str,
    rfx_summary: str,
) -> Message:
    """Send an RFQ notification as an in-app system message.

    Args:
        session: Active database session.
        thread_id: Target thread ID.
        rfx_title: Title of the RFQ.
        rfx_summary: Summary text for the RFQ.

    Returns:
        The persisted Message instance.
    """
    body = (
        f"You have received a new RFQ: {rfx_title}\n\n"
        f"{rfx_summary}\n\n"
        f"Please submit your quote through this portal."
    )
    return await deliver_in_app(session, thread_id, body, sender_kind="system")


def get_unread_count(
    session: Session,
    thread_id: int,
    last_seen_message_id: int = 0,
) -> int:
    """Count messages on a thread newer than last_seen_message_id.

    Args:
        session: Active database session.
        thread_id: Thread to count messages in.
        last_seen_message_id: Only count messages with id > this value.

    Returns:
        Number of unread messages.
    """
    messages = list(
        session.exec(
            select(Message).where(
                Message.thread_id == thread_id,
                Message.id > last_seen_message_id,
            )
        ).all()
    )
    return len(messages)

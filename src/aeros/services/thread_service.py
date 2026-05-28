"""Thread and message operations for RFx vendor communication."""

from sqlmodel import Session, select

from aeros.models.rfx import Attachment, Message, Thread


def get_or_create_thread(session: Session, rfx_id: int, vendor_id: int) -> Thread:
    """Return the existing thread for an RFx+vendor, or create one.

    Args:
        session: Active database session.
        rfx_id: The RFx run id.
        vendor_id: The vendor id.

    Returns:
        The Thread row (existing or newly created).
    """
    thread = session.exec(
        select(Thread).where(Thread.rfx_id == rfx_id, Thread.vendor_id == vendor_id)
    ).first()
    if not thread:
        thread = Thread(rfx_id=rfx_id, vendor_id=vendor_id)
        session.add(thread)
        session.commit()
        session.refresh(thread)
    return thread


def add_message(
    session: Session,
    thread_id: int,
    *,
    sender_user_id: int | None = None,
    sender_kind: str = "system",
    channel: str = "in_app",
    body_text: str = "",
    body_html: str | None = None,
    parent_message_id: int | None = None,
) -> Message:
    """Create a new message in a thread.

    Args:
        session: Active database session.
        thread_id: The thread to add the message to.
        sender_user_id: User id of the sender (None for system messages).
        sender_kind: One of buyer, vendor, system, agent.
        channel: One of email, telegram, in_app, system.
        body_text: Plain-text body.
        body_html: Optional HTML body.
        parent_message_id: Optional id for threaded replies.

    Returns:
        The newly created Message row.
    """
    msg = Message(
        thread_id=thread_id,
        sender_user_id=sender_user_id,
        sender_kind=sender_kind,
        channel=channel,
        body_text=body_text,
        body_html=body_html,
        parent_message_id=parent_message_id,
    )
    session.add(msg)
    session.commit()
    session.refresh(msg)
    return msg


def get_thread_messages(session: Session, thread_id: int) -> list[Message]:
    """Return all messages for a thread, ordered by creation time.

    Args:
        session: Active database session.
        thread_id: The thread to fetch messages for.

    Returns:
        List of Message rows in chronological order.
    """
    return list(
        session.exec(
            select(Message).where(Message.thread_id == thread_id).order_by(Message.created_at)
        ).all()
    )


def get_thread_attachments(session: Session, thread_id: int) -> list[Attachment]:
    """Return all attachments for messages in a thread.

    Args:
        session: Active database session.
        thread_id: The thread to fetch attachments for.

    Returns:
        List of Attachment rows belonging to thread messages.
    """
    messages = get_thread_messages(session, thread_id)
    msg_ids = [m.id for m in messages]
    if not msg_ids:
        return []
    return list(
        session.exec(
            select(Attachment).where(Attachment.message_id.in_(msg_ids))  # type: ignore[union-attr]
        ).all()
    )

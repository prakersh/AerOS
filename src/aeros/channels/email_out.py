"""SMTP outbound — sends RFx invitations and notifications to vendors."""

from email.message import EmailMessage

import aiosmtplib

from aeros.config import settings


async def send_rfx_invitation(
    to_email: str,
    vendor_name: str,
    rfx_title: str,
    rfx_summary: str,
    correlation_token: str,
    portal_url: str,
) -> bool:
    short_token = correlation_token[:20] + "..."
    reply_to = f"procurement+{correlation_token}@{settings.smtp_from_address.split('@')[1]}"

    msg = EmailMessage()
    msg["From"] = f"AEROS Procurement <{settings.smtp_from_address}>"
    msg["To"] = to_email
    msg["Subject"] = f"[RFQ] {rfx_title}"
    msg["Reply-To"] = reply_to

    body = f"""Hi {vendor_name},

You have received a new Request for Quotation (RFQ):

{rfx_title}

{rfx_summary}

Please submit your quote by replying to this email with your price list attached (PDF, Word, Excel, or image of your rate card), or log in to submit directly:

{portal_url}

Best regards,
AEROS Procurement System
"""
    msg.set_content(body)

    html = f"""
<div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
    <h2 style="color: #4f46e5;">New RFQ: {rfx_title}</h2>
    <p>Hi {vendor_name},</p>
    <p>You have received a new Request for Quotation:</p>
    <div style="background: #f4f4f5; border-radius: 8px; padding: 16px; margin: 16px 0;">
        <pre style="white-space: pre-wrap; font-size: 14px;">{rfx_summary}</pre>
    </div>
    <p>Please submit your quote by:</p>
    <ul>
        <li><strong>Replying to this email</strong> with your price list attached (PDF, Word, Excel, or image)</li>
        <li>Or <a href="{portal_url}" style="color: #4f46e5;">log in to the portal</a></li>
    </ul>
    <hr style="border: none; border-top: 1px solid #e4e4e7; margin: 24px 0;">
    <p style="color: #71717a; font-size: 12px;">AEROS Procurement System</p>
</div>
"""
    msg.add_alternative(html, subtype="html")

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username or None,
            password=settings.smtp_password or None,
            start_tls=settings.smtp_use_tls,
        )
        return True
    except Exception:
        return False


async def send_po_email(
    to_email: str,
    vendor_name: str,
    po_number: str,
    pdf_path: str,
) -> bool:
    msg = EmailMessage()
    msg["From"] = f"AEROS Procurement <{settings.smtp_from_address}>"
    msg["To"] = to_email
    msg["Subject"] = f"[PO] Purchase Order {po_number}"

    msg.set_content(f"""Hi {vendor_name},

Please find attached your Purchase Order {po_number}.

Best regards,
AEROS Procurement System
""")

    with open(pdf_path, "rb") as f:
        msg.add_attachment(
            f.read(),
            maintype="application",
            subtype="pdf",
            filename=f"PO_{po_number}.pdf",
        )

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username or None,
            password=settings.smtp_password or None,
            start_tls=settings.smtp_use_tls,
        )
        return True
    except Exception:
        return False

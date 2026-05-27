"""Tests for email_out channel — SMTP outbound functionality."""

from unittest.mock import AsyncMock, patch


class TestSendRfxInvitation:
    async def test_send_success(self, tmp_path):
        """Should return True on successful send."""
        from aeros.channels.email_out import send_rfx_invitation

        with patch("aeros.channels.email_out.aiosmtplib.send", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = None
            result = await send_rfx_invitation(
                to_email="vendor@test.com",
                vendor_name="Test Vendor",
                rfx_title="Q3 Vegetables",
                rfx_summary="Need 100kg rice",
                correlation_token="abc123token_long_enough_here",
                portal_url="http://localhost:5173/portal/abc",
            )
            assert result is True
            mock_send.assert_called_once()

    async def test_send_failure_returns_false(self):
        """Should return False when SMTP fails."""
        from aeros.channels.email_out import send_rfx_invitation

        with patch("aeros.channels.email_out.aiosmtplib.send", new_callable=AsyncMock) as mock_send:
            mock_send.side_effect = Exception("SMTP connection failed")
            result = await send_rfx_invitation(
                to_email="vendor@test.com",
                vendor_name="Test Vendor",
                rfx_title="Test RFx",
                rfx_summary="Summary",
                correlation_token="tok123",
                portal_url="http://localhost",
            )
            assert result is False


class TestSendPoEmail:
    async def test_send_po_success(self, tmp_path):
        """Should return True on successful PO email send."""
        from aeros.channels.email_out import send_po_email

        # Create a fake PDF file
        pdf_path = tmp_path / "test_po.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 fake pdf content")

        with patch("aeros.channels.email_out.aiosmtplib.send", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = None
            result = await send_po_email(
                to_email="vendor@test.com",
                vendor_name="Test Vendor",
                po_number="PO-2026-001",
                pdf_path=str(pdf_path),
            )
            assert result is True
            mock_send.assert_called_once()

    async def test_send_po_failure_returns_false(self, tmp_path):
        """Should return False when SMTP fails for PO email."""
        from aeros.channels.email_out import send_po_email

        pdf_path = tmp_path / "test_po.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 fake")

        with patch("aeros.channels.email_out.aiosmtplib.send", new_callable=AsyncMock) as mock_send:
            mock_send.side_effect = Exception("Connection refused")
            result = await send_po_email(
                to_email="vendor@test.com",
                vendor_name="Test Vendor",
                po_number="PO-2026-001",
                pdf_path=str(pdf_path),
            )
            assert result is False

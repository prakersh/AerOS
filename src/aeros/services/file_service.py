"""File validation and management service."""

import hashlib
import mimetypes
import os
from dataclasses import dataclass

from aeros.config import settings

# Kept in sync with MIME_ROUTER in aeros.ai.extractors.router — every allowed
# type must have an extractor, or uploads silently degrade to a stub string.
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/msword",
    "text/csv",
    "text/tab-separated-values",
    "text/plain",
    "text/html",
    "image/jpeg",
    "image/png",
    "image/webp",
}

BLOCKED_EXTENSIONS = {".exe", ".bat", ".cmd", ".sh", ".ps1", ".vbs", ".js", ".msi"}


@dataclass
class FileValidation:
    """Result of file validation checks."""

    is_valid: bool
    mime_type: str
    size_bytes: int
    sha256: str
    error: str = ""


def _sniff_magic_bytes(content: bytes) -> str | None:
    """Best-effort MIME detection from leading bytes, no native libs required."""
    head = content[:16]
    if head.startswith(b"%PDF"):
        return "application/pdf"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return "image/webp"
    if head.startswith(b"PK\x03\x04"):
        # OOXML zip container — can't distinguish docx/xlsx from bytes alone;
        # defer to the extension-based guess for the precise subtype.
        return None
    stripped = content[:512].lstrip().lower()
    if stripped.startswith((b"<!doctype html", b"<html")):
        return "text/html"
    try:
        text = content[:4096].decode("utf-8")
    except UnicodeDecodeError:
        return None
    if text and all(ch.isprintable() or ch in "\r\n\t" for ch in text):
        return "text/plain"
    return None


def _detect_mime(content: bytes, filename: str) -> str:
    """Detect MIME type: python-magic if available, then extension, then content sniff."""
    try:
        import magic

        result: str = magic.from_buffer(content[:8192], mime=True)
        if result and result != "application/octet-stream":
            return result
    except Exception:  # noqa: S110 — python-magic is optional; fall back silently
        pass

    mime, _ = mimetypes.guess_type(filename)
    if mime:
        return mime

    sniffed = _sniff_magic_bytes(content)
    return sniffed or "application/octet-stream"


def validate_file(content: bytes, filename: str) -> FileValidation:
    """Validate file content and metadata.

    Checks: blocked extensions, size limits, empty files, MIME type allowlist.

    Args:
        content: Raw file bytes.
        filename: Original filename (used for extension and MIME detection).

    Returns:
        FileValidation with is_valid=True on success, or error details on failure.
    """
    size = len(content)
    max_size = settings.max_upload_size_mb * 1024 * 1024
    sha = hashlib.sha256(content).hexdigest()

    ext = os.path.splitext(filename)[1].lower()
    if ext in BLOCKED_EXTENSIONS:
        return FileValidation(False, "", size, sha, f"Blocked file extension: {ext}")

    if size > max_size:
        return FileValidation(
            False, "", size, sha, f"File too large: {size} bytes (max {max_size})"
        )

    if size == 0:
        return FileValidation(False, "", size, sha, "Empty file")

    mime = _detect_mime(content, filename)

    if mime not in ALLOWED_MIME_TYPES:
        return FileValidation(False, mime, size, sha, f"Unsupported file type: {mime}")

    return FileValidation(True, mime, size, sha)


def save_file(content: bytes, rfx_id: int, vendor_id: int, filename: str) -> str:
    """Save file content to disk under upload_dir/rfx_id/vendor_id/.

    Args:
        content: Raw file bytes.
        rfx_id: RFx run identifier.
        vendor_id: Vendor identifier.
        filename: Original filename.

    Returns:
        Absolute path to the saved file.
    """
    upload_dir = os.path.join(settings.upload_dir, str(rfx_id), str(vendor_id))
    os.makedirs(upload_dir, exist_ok=True)
    sha = hashlib.sha256(content).hexdigest()
    safe_name = f"{sha[:8]}_{filename}"
    path = os.path.join(upload_dir, safe_name)
    with open(path, "wb") as f:
        f.write(content)
    return path

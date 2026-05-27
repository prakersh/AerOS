"""Tests for file_service — validation, MIME detection, and file saving."""

import os
import tempfile

import pytest

from aeros.services.file_service import (
    ALLOWED_MIME_TYPES,
    BLOCKED_EXTENSIONS,
    FileValidation,
    save_file,
    validate_file,
)


class TestValidateFile:
    """Tests for validate_file()."""

    def test_empty_file_rejected(self):
        """Empty files should be rejected."""
        result = validate_file(b"", "test.pdf")
        assert result.is_valid is False
        assert "Empty file" in result.error

    def test_blocked_extension_rejected(self):
        """Files with blocked extensions like .exe should be rejected."""
        result = validate_file(b"MZ\x00\x00", "malware.exe")
        assert result.is_valid is False
        assert "Blocked file extension" in result.error

    def test_blocked_extension_bat(self):
        """Batch files should be blocked."""
        result = validate_file(b"echo hello", "script.bat")
        assert result.is_valid is False
        assert ".bat" in result.error

    def test_blocked_extension_ps1(self):
        """PowerShell scripts should be blocked."""
        result = validate_file(b"Write-Host", "script.ps1")
        assert result.is_valid is False
        assert ".ps1" in result.error

    def test_file_too_large(self):
        """Files exceeding max size should be rejected."""
        # Default max is 25MB — create content just over that
        from aeros.config import settings

        max_size = settings.max_upload_size_mb * 1024 * 1024
        big_content = b"X" * (max_size + 1)
        result = validate_file(big_content, "big.txt")
        assert result.is_valid is False
        assert "too large" in result.error

    def test_valid_text_file(self):
        """A plain text file with .txt extension should pass validation."""
        content = b"Hello, world. This is a plain text file for testing."
        result = validate_file(content, "readme.txt")
        assert result.is_valid is True
        assert result.size_bytes == len(content)
        assert len(result.sha256) == 64  # SHA-256 hex digest

    def test_valid_csv_file(self):
        """CSV files should pass validation."""
        content = b"name,price,qty\nMilk,50,100\nButter,200,50\n"
        result = validate_file(content, "prices.csv")
        assert result.is_valid is True
        assert result.size_bytes == len(content)

    def test_sha256_computed_correctly(self):
        """SHA-256 hash should be computed correctly."""
        import hashlib

        content = b"deterministic content for hashing"
        expected = hashlib.sha256(content).hexdigest()
        result = validate_file(content, "test.txt")
        assert result.sha256 == expected

    def test_blocked_js_extension(self):
        """JavaScript files should be blocked."""
        result = validate_file(b"alert(1)", "payload.js")
        assert result.is_valid is False
        assert ".js" in result.error

    def test_case_insensitive_extension_blocking(self):
        """Extension blocking should be case-insensitive."""
        result = validate_file(b"MZ\x00\x00", "virus.EXE")
        assert result.is_valid is False
        assert "Blocked file extension" in result.error


class TestSaveFile:
    """Tests for save_file()."""

    def test_save_creates_file(self, tmp_path, monkeypatch):
        """save_file should write content to disk and return path."""
        monkeypatch.setattr("aeros.services.file_service.settings.upload_dir", str(tmp_path))
        content = b"PDF content here"
        path = save_file(content, rfx_id=1, vendor_id=2, filename="quote.pdf")
        assert os.path.exists(path)
        with open(path, "rb") as f:
            assert f.read() == content

    def test_save_creates_nested_dirs(self, tmp_path, monkeypatch):
        """save_file should create rfx_id/vendor_id subdirectories."""
        monkeypatch.setattr("aeros.services.file_service.settings.upload_dir", str(tmp_path))
        path = save_file(b"data", rfx_id=42, vendor_id=7, filename="doc.xlsx")
        assert "/42/7/" in path or "\\42\\7\\" in path

    def test_save_filename_includes_hash_prefix(self, tmp_path, monkeypatch):
        """Saved filename should be prefixed with first 8 chars of SHA-256."""
        import hashlib

        monkeypatch.setattr("aeros.services.file_service.settings.upload_dir", str(tmp_path))
        content = b"unique content"
        sha_prefix = hashlib.sha256(content).hexdigest()[:8]
        path = save_file(content, rfx_id=1, vendor_id=1, filename="test.pdf")
        assert sha_prefix in os.path.basename(path)


class TestConstants:
    """Tests for module-level constants."""

    def test_pdf_is_allowed(self):
        assert "application/pdf" in ALLOWED_MIME_TYPES

    def test_xlsx_is_allowed(self):
        assert (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            in ALLOWED_MIME_TYPES
        )

    def test_exe_is_blocked(self):
        assert ".exe" in BLOCKED_EXTENSIONS

    def test_sh_is_blocked(self):
        assert ".sh" in BLOCKED_EXTENSIONS

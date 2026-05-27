import re

PII_PATTERNS = {
    "aadhaar": re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"),
    "pan": re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"),
    "phone_in": re.compile(r"\b(?:\+91[\s-]?)?[6-9]\d{9}\b"),
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "credit_card": re.compile(r"\b(?:\d{4}[\s-]?){3}\d{4}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
}

REDACTION_MAP = {
    "aadhaar": "[AADHAAR_REDACTED]",
    "pan": "[PAN_REDACTED]",
    "phone_in": "[PHONE_REDACTED]",
    "email": "[EMAIL_REDACTED]",
    "credit_card": "[CC_REDACTED]",
    "ssn": "[SSN_REDACTED]",
}

DANGEROUS_OUTPUT_PATTERNS = [
    re.compile(r"<script\b", re.IGNORECASE),
    re.compile(r"javascript:", re.IGNORECASE),
    re.compile(r"on\w+\s*=", re.IGNORECASE),
]


class OutputFilter:
    def __init__(self, redact_pii: bool = True) -> None:
        self.redact_pii = redact_pii

    def filter(self, text: str) -> tuple[str, list[str]]:
        """Returns (filtered_text, list_of_redactions_applied)."""
        redactions: list[str] = []
        result = text
        if self.redact_pii:
            for pii_type, pattern in PII_PATTERNS.items():
                if pattern.search(result):
                    result = pattern.sub(REDACTION_MAP[pii_type], result)
                    redactions.append(pii_type)
        for pattern in DANGEROUS_OUTPUT_PATTERNS:
            result = pattern.sub("[SANITIZED]", result)
        return result, redactions

    def check_safety(self, text: str) -> tuple[bool, str]:
        """Check if output contains anything dangerous."""
        for pattern in DANGEROUS_OUTPUT_PATTERNS:
            if pattern.search(text):
                return False, "Output contains potentially dangerous content"
        return True, ""

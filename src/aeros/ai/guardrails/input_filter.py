import re

JAILBREAK_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"forget\s+(all\s+)?your\s+(instructions|rules|guidelines)",
    r"you\s+are\s+now\s+(a|an)\s+\w+\s+(that|who)\s+(can|will|should)",
    r"pretend\s+(to\s+be|you\s+are)",
    r"act\s+as\s+(if|though|a)\b",
    r"do\s+not\s+follow\s+(your|any)\s+(rules|guidelines|instructions)",
    r"override\s+(your|all)\s+(rules|restrictions|safety)",
    r"system\s*prompt\s*:",
    r"\[SYSTEM\]",
    r"<\|im_start\|>",
    r"<\|system\|>",
    r"</?(system|instruction|prompt)>",
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in JAILBREAK_PATTERNS]

SQL_INJECTION_PATTERNS = [
    r";\s*(DROP|DELETE|INSERT|UPDATE|ALTER|EXEC)\s",
    r"'\s*(OR|AND)\s+\d+=\d+",
    r"UNION\s+(ALL\s+)?SELECT",
]

COMPILED_SQL = [re.compile(p, re.IGNORECASE) for p in SQL_INJECTION_PATTERNS]


class InputFilter:
    def check(self, text: str) -> tuple[bool, str]:
        """Returns (is_safe, reason). is_safe=True means input is OK."""
        for pattern in COMPILED_PATTERNS:
            if pattern.search(text):
                return False, "Potential prompt injection detected"
        for pattern in COMPILED_SQL:
            if pattern.search(text):
                return False, "Potential SQL injection detected"
        if len(text) > 50_000:
            return False, "Input exceeds maximum length (50,000 chars)"
        return True, ""

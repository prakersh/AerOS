"""Email body extractor — handles HTML, plaintext, and forwarded chains."""

import re


async def extract_email_body(file_path: str, **kwargs) -> str:
    with open(file_path, encoding="utf-8", errors="replace") as f:
        content = f.read()

    if "<html" in content.lower() or "<body" in content.lower():
        return _extract_html(content)
    return _extract_plaintext(content)


def _extract_html(html: str) -> str:
    try:
        import bleach
        text = bleach.clean(html, tags=[], strip=True)
    except ImportError:
        text = re.sub(r"<[^>]+>", "", html)

    return _strip_forwarded_chains(text)


def _extract_plaintext(text: str) -> str:
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.lstrip("> ")
        if stripped.startswith("On ") and "wrote:" in stripped:
            break
        if stripped.startswith("---------- Forwarded message"):
            break
        cleaned.append(stripped)

    return "\n".join(cleaned).strip()


def _strip_forwarded_chains(text: str) -> str:
    patterns = [
        r"On .+ wrote:.*",
        r"-+ Forwarded message -+.*",
        r"From: .+\nSent: .+\nTo: .+\nSubject: .+",
    ]
    for pat in patterns:
        text = re.split(pat, text, maxsplit=1, flags=re.IGNORECASE)[0]
    return text.strip()

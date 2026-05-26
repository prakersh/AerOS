"""PDF extractor — handles both digital (text-layer) and scanned PDFs."""

import pymupdf


async def extract_pdf(file_path: str, **kwargs) -> str:
    try:
        import pymupdf4llm
        md = pymupdf4llm.to_markdown(file_path)
        if md and len(md.strip()) > 50:
            return md
    except Exception:
        pass

    doc = pymupdf.open(file_path)
    text_parts = []
    for page in doc:
        text = page.get_text()
        if text.strip():
            text_parts.append(f"--- Page {page.number + 1} ---\n{text}")

    if text_parts:
        return "\n".join(text_parts)

    # Scanned PDF — would need vision provider for OCR
    # For now, return placeholder indicating vision needed
    return "[Scanned PDF detected — requires vision extraction]"

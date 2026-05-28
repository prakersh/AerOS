"""PDF extractor — handles both digital (text-layer) and scanned PDFs."""

from typing import Any

import pymupdf


async def extract_pdf(file_path: str, *, vision_provider: Any = None, **kwargs: Any) -> str:
    try:
        import pymupdf4llm

        md = pymupdf4llm.to_markdown(file_path)
        if md and len(md.strip()) > 50:
            return str(md)
    except Exception:  # noqa: S110
        pass

    doc = pymupdf.open(file_path)  # type: ignore[no-untyped-call]
    text_parts = []
    for page in doc:  # type: ignore[attr-defined]
        text = page.get_text()
        if text.strip():
            text_parts.append(f"--- Page {page.number + 1} ---\n{text}")

    if text_parts:
        return "\n".join(text_parts)

    if not vision_provider:
        return "[Scanned PDF detected — no vision provider available for OCR]"

    ocr_parts = []
    for page in doc:  # type: ignore[attr-defined]
        pix = page.get_pixmap(dpi=200)
        image_data = pix.tobytes("png")
        prompt = (
            "Extract all text and pricing information from this scanned document page. "
            "This is page from a vendor's quotation or rate card. "
            "Preserve the structure — tables, line items, prices, units, and terms."
        )
        result = await vision_provider.vision(image_data, prompt, mime_type="image/png")
        ocr_parts.append(f"--- Page {page.number + 1} ---\n{result.content}")

    return "\n".join(ocr_parts) if ocr_parts else "[Empty scanned PDF]"

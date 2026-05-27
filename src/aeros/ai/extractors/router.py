"""Format router — dispatches to the correct extractor based on MIME type."""

from aeros.ai.extractors.email_body import extract_email_body
from aeros.ai.extractors.image import extract_image
from aeros.ai.extractors.pdf import extract_pdf
from aeros.ai.extractors.spreadsheet import extract_spreadsheet
from aeros.ai.extractors.word import extract_word

MIME_ROUTER = {
    "application/pdf": extract_pdf,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": extract_word,
    "application/msword": extract_word,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": extract_spreadsheet,
    "application/vnd.ms-excel": extract_spreadsheet,
    "text/csv": extract_spreadsheet,
    "text/tab-separated-values": extract_spreadsheet,
    "image/jpeg": extract_image,
    "image/png": extract_image,
    "image/webp": extract_image,
    "text/plain": extract_email_body,
    "text/html": extract_email_body,
}


async def route_extraction(
    file_path: str,
    mime_type: str,
    vision_provider=None,
) -> str:
    extractor = MIME_ROUTER.get(mime_type)
    if not extractor:
        return f"[Unsupported format: {mime_type}]"

    if mime_type.startswith("image/") or mime_type == "application/pdf":
        return await extractor(file_path, vision_provider=vision_provider)
    return await extractor(file_path)

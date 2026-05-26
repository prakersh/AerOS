"""Image extractor — uses vision model to read photographed rate cards."""


async def extract_image(file_path: str, *, vision_provider=None, **kwargs) -> str:
    if not vision_provider:
        return "[Image extraction requires a vision provider]"

    with open(file_path, "rb") as f:
        image_data = f.read()

    mime_type = "image/jpeg"
    if file_path.endswith(".png"):
        mime_type = "image/png"
    elif file_path.endswith(".webp"):
        mime_type = "image/webp"

    prompt = (
        "Extract all pricing information from this image. "
        "This is a vendor's rate card or price list for a procurement quote. "
        "List every item with its name, price, unit, and any other details visible. "
        "Format as a structured list."
    )

    result = await vision_provider.vision(image_data, prompt, mime_type=mime_type)
    return result.content

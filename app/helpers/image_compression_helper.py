import base64
import io

from PIL import Image


def compress_image_to_target(original_image_bytes: bytes, target_kb: int = 120) -> str:
    img = Image.open(io.BytesIO(original_image_bytes))

    if img.mode in ("RGBA", "P"):
        img_converted = img.convert("RGBA")
    else:
        img_converted = img.convert("RGB")

    target_bytes = target_kb * 1024

    output_buffer = io.BytesIO()
    img_converted.save(output_buffer, format="WEBP", quality=80)
    webp_size = len(output_buffer.getvalue())

    if webp_size <= target_bytes:
        return base64.b64encode(output_buffer.getvalue()).decode("utf-8")

    quality = _calculate_initial_quality(webp_size, target_bytes)

    for attempt in range(2):
        output_buffer = io.BytesIO()
        img_converted.save(output_buffer, format="WEBP", quality=quality)
        compressed_size = len(output_buffer.getvalue())

        if compressed_size <= target_bytes:
            return base64.b64encode(output_buffer.getvalue()).decode("utf-8")

        quality = max(40, quality - 10)

    if compressed_size > target_bytes and max(img_converted.size) > 1024:
        img_resized = _resize_image(img_converted, target_bytes, compressed_size)
        output_buffer = io.BytesIO()
        img_resized.save(output_buffer, format="WEBP", quality=70)
        return base64.b64encode(output_buffer.getvalue()).decode("utf-8")

    return base64.b64encode(output_buffer.getvalue()).decode("utf-8")


def _calculate_initial_quality(current_size: int, target_size: int) -> int:
    ratio = target_size / current_size

    if ratio >= 0.8:
        return 75
    elif ratio >= 0.5:
        return 65
    elif ratio >= 0.3:
        return 55
    else:
        return 45


def _resize_image(img: Image, target_bytes: int, current_bytes: int) -> Image:
    ratio = (target_bytes / current_bytes) ** 0.5
    new_width = int(img.width * ratio)
    new_height = int(img.height * ratio)

    max_dimension = 1920
    if new_width > max_dimension or new_height > max_dimension:
        if new_width > new_height:
            new_height = int(new_height * max_dimension / new_width)
            new_width = max_dimension
        else:
            new_width = int(new_width * max_dimension / new_height)
            new_height = max_dimension

    return img.resize((new_width, new_height), Image.Resampling.LANCZOS)

import base64
import io
from typing import Optional

from PIL import Image

# Safety limit: reject images over 25 megapixels (prevents decompression bombs)
Image.MAX_IMAGE_PIXELS = 25_000_000


def compress_image_to_target(original_image_bytes: bytes, target_kb: int = 120, max_width: Optional[int] = None) -> str:
    img = Image.open(io.BytesIO(original_image_bytes))
    img_converted = None
    try:
        if img.mode in ("RGBA", "P"):
            img_converted = img.convert("RGBA")
        else:
            img_converted = img.convert("RGB")

        # Close original if convert created a new image
        if img_converted is not img:
            img.close()
            img = None

        if max_width and img_converted.width > max_width:
            ratio = max_width / img_converted.width
            new_height = int(img_converted.height * ratio)
            img_old = img_converted
            img_converted = img_converted.resize((max_width, new_height), Image.Resampling.LANCZOS)
            img_old.close()

        target_bytes = target_kb * 1024

        output_buffer = io.BytesIO()
        img_converted.save(output_buffer, format="WEBP", quality=80)
        result_bytes = output_buffer.getvalue()

        if len(result_bytes) <= target_bytes:
            return base64.b64encode(result_bytes).decode("utf-8")

        quality = _calculate_initial_quality(len(result_bytes), target_bytes)

        for attempt in range(2):
            output_buffer = io.BytesIO()
            img_converted.save(output_buffer, format="WEBP", quality=quality)
            result_bytes = output_buffer.getvalue()

            if len(result_bytes) <= target_bytes:
                return base64.b64encode(result_bytes).decode("utf-8")

            quality = max(40, quality - 10)

        if len(result_bytes) > target_bytes and max(img_converted.size) > 1024:
            img_resized = _resize_image(img_converted, target_bytes, len(result_bytes))
            img_converted.close()
            img_converted = img_resized

            output_buffer = io.BytesIO()
            img_converted.save(output_buffer, format="WEBP", quality=70)
            result_bytes = output_buffer.getvalue()

        return base64.b64encode(result_bytes).decode("utf-8")
    finally:
        if img is not None:
            img.close()
        if img_converted is not None:
            img_converted.close()


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

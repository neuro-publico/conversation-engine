import asyncio
import os

MAX_CONCURRENT_IMAGE_REQUESTS = int(os.environ.get("MAX_CONCURRENT_IMAGE_REQUESTS", "15"))

_image_semaphore = None


def get_image_semaphore():
    """Lazy-init semaphore (must be created inside a running event loop)."""
    global _image_semaphore
    if _image_semaphore is None:
        _image_semaphore = asyncio.Semaphore(MAX_CONCURRENT_IMAGE_REQUESTS)
    return _image_semaphore

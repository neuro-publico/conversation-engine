import asyncio
import logging
from typing import Dict, Optional

import httpx

from app.configurations.config import API_KEY

logger = logging.getLogger(__name__)


async def post_callback(
    url: str,
    payload: Dict,
    max_retries: int = 3,
    api_key: Optional[str] = None,
) -> None:
    key = api_key or API_KEY

    for attempt in range(1, max_retries + 1):
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={"x-api-key": key, "Content-Type": "application/json"},
                )
                response.raise_for_status()
                logger.info(f"Callback POST successful to {url} (attempt {attempt})")
                return
        except Exception as e:
            logger.warning(f"Callback POST attempt {attempt}/{max_retries} failed: {type(e).__name__}: {e}")
            if attempt < max_retries:
                await asyncio.sleep(2**attempt)

    logger.error(f"Callback POST failed after {max_retries} attempts to {url}")

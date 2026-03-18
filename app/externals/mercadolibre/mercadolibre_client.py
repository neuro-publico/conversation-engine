import logging
import time
from typing import Any, Dict, Optional

import httpx

from app.configurations.config import MERCADOLIBRE_CLIENT_ID, MERCADOLIBRE_CLIENT_SECRET

logger = logging.getLogger(__name__)

BASE_URL = "https://api.mercadolibre.com"

_cached_token: Optional[str] = None
_token_expires_at: float = 0


async def _get_access_token() -> str:
    global _cached_token, _token_expires_at

    if _cached_token and time.time() < _token_expires_at:
        return _cached_token

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": MERCADOLIBRE_CLIENT_ID,
                "client_secret": MERCADOLIBRE_CLIENT_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

    print(f"[DEBUG ML OAuth] status: {response.status_code}")
    print(f"[DEBUG ML OAuth] response: {data}")

    _cached_token = data["access_token"]
    _token_expires_at = time.time() + data.get("expires_in", 21600) - 300
    logger.info("MercadoLibre access token obtained")
    return _cached_token


async def get_product_details(product_id: str) -> Dict[str, Any]:
    token = await _get_access_token()

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/products/{product_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()

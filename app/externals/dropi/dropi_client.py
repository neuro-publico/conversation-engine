import httpx
from typing import Dict, Any

from app.configurations.config import DROPI_API_URL, DROPI_API_KEY


async def get_product_details(product_id: str) -> Dict[str, Any]:
    headers = {
        "dropi-integration-key": DROPI_API_KEY
    }

    url = f"{DROPI_API_URL}/{product_id}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise Exception(f"API request failed with status {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            raise Exception(f"API request failed: {str(e)}") 
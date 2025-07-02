import httpx
from typing import Dict, Any

from app.configurations.config import DROPI_HOST, DROPI_API_KEY


async def get_product_details(product_id: str) -> Dict[str, Any]:
    headers = {
        "dropi-integration-key": DROPI_API_KEY
    }

    url = f"{DROPI_HOST}/integrations/products/v2/{product_id}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise Exception(f"API request failed with status {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            raise Exception(f"API request failed: {str(e)}")


async def get_departments() -> Dict[str, Any]:
    headers = {
        "dropi-integration-key": DROPI_API_KEY
    }
    url = f"{DROPI_HOST}/integrations/department"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise Exception(f"API request failed with status {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            raise Exception(f"API request failed: {str(e)}")


async def get_cities_by_department(department_id: int, rate_type: str) -> Dict[str, Any]:
    headers = {
        "dropi-integration-key": DROPI_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "department_id": department_id,
        "rate_type": rate_type
    }
    url = f"{DROPI_HOST}/integrations/trajectory/bycity"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise Exception(f"API request failed with status {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            raise Exception(f"API request failed: {str(e)}") 
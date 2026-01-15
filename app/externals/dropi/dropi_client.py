from typing import Any, Dict

import httpx

from app.configurations.config import DROPI_HOST, get_dropi_api_key


async def get_product_details(product_id: str, country: str = "co") -> Dict[str, Any]:
    headers = {"dropi-integration-key": get_dropi_api_key(country)}

    dropi_host = DROPI_HOST.replace(".co", f".{country}")
    url = f"{dropi_host}/integrations/products/v2/{product_id}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise Exception(f"API request failed with status {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            raise Exception(f"API request failed: {str(e)}")


async def get_departments(country: str = "co") -> Dict[str, Any]:
    headers = {"dropi-integration-key": get_dropi_api_key(country)}
    dropi_host = DROPI_HOST.replace(".co", f".{country}")
    url = f"{dropi_host}/integrations/department"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise Exception(f"API request failed with status {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            raise Exception(f"API request failed: {str(e)}")


async def get_cities_by_department(department_id: int, rate_type: str, country: str = "co") -> Dict[str, Any]:
    headers = {"dropi-integration-key": get_dropi_api_key(country), "Content-Type": "application/json"}
    payload = {"department_id": department_id, "rate_type": rate_type}
    dropi_host = DROPI_HOST.replace(".co", f".{country}")
    url = f"{dropi_host}/integrations/trajectory/bycity"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise Exception(f"API request failed with status {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            raise Exception(f"API request failed: {str(e)}")

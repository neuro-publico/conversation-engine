import json
import logging
from typing import Any, Dict

import httpx

from app.configurations.config import DROPI_COOKIE_PY, get_dropi_api_key, get_dropi_host

logger = logging.getLogger(__name__)


def _parse_json_response(response: httpx.Response) -> Dict[str, Any]:
    """Parsea el body como JSON o lanza con mensaje claro si está vacío o no es JSON."""
    text = response.text
    if not text or not text.strip():
        raise Exception(
            f"Dropi API returned empty body (status {response.status_code}). " "Check URL and API key for this country."
        )
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning("Dropi API response is not JSON. status=%s body=%s", response.status_code, text[:500])
        raise Exception(
            f"Dropi API returned invalid JSON (status {response.status_code}): {e}. "
            f"Body starts with: {repr(text[:200])}"
        )


def _log_dropi_request(method: str, url: str, headers: Dict[str, str], json_body: Dict[str, Any] | None = None) -> None:
    """Log de la petición a Dropi en formato similar a curl para depuración."""
    header_args = " ".join(f"-H '{k}: {v}'" for k, v in headers.items())
    body_args = ""
    if json_body:
        body_args = f" -d '{json.dumps(json_body)}'"
    curl_like = f"curl -X {method} '{url}' {header_args}{body_args}"
    logger.info("Dropi API request: %s", curl_like)


async def get_product_details(product_id: str, country: str = "co") -> Dict[str, Any]:
    country_normalized = country.lower() if country else "co"
    dropi_host = get_dropi_host(country)
    headers = {"dropi-integration-key": get_dropi_api_key(country_normalized)}
    if country_normalized == "py":
        headers["accept"] = "application/json, text/plain, */*"
        if DROPI_COOKIE_PY:
            headers["Cookie"] = DROPI_COOKIE_PY
    url = f"{dropi_host}/integrations/products/v2/{product_id}"

    _log_dropi_request("GET", url, headers)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return _parse_json_response(response)
        except httpx.HTTPStatusError as e:
            raise Exception(f"API request failed with status {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            raise Exception(f"API request failed: {str(e)}")


async def get_departments(country: str = "co") -> Dict[str, Any]:
    country_normalized = country.lower() if country else "co"
    headers = {"dropi-integration-key": get_dropi_api_key(country_normalized)}
    dropi_host = get_dropi_host(country)
    url = f"{dropi_host}/integrations/department"
    _log_dropi_request("GET", url, headers)
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return _parse_json_response(response)
        except httpx.HTTPStatusError as e:
            raise Exception(f"API request failed with status {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            raise Exception(f"API request failed: {str(e)}")


async def get_cities_by_department(department_id: int, rate_type: str, country: str = "co") -> Dict[str, Any]:
    country_normalized = country.lower() if country else "co"
    headers = {"dropi-integration-key": get_dropi_api_key(country_normalized), "Content-Type": "application/json"}
    payload = {"department_id": department_id, "rate_type": rate_type}
    dropi_host = get_dropi_host(country)
    url = f"{dropi_host}/integrations/trajectory/bycity"
    _log_dropi_request("POST", url, headers, payload)
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return _parse_json_response(response)
        except httpx.HTTPStatusError as e:
            raise Exception(f"API request failed with status {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            raise Exception(f"API request failed: {str(e)}")

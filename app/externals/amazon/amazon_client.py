from typing import Any, Dict

import httpx

from app.configurations.config import RAPIDAPI_KEY
from app.externals.amazon.requests.amazon_search_request import AmazonSearchRequest
from app.externals.amazon.responses.amazon_search_response import AmazonSearchResponse


async def search_products(request: AmazonSearchRequest) -> AmazonSearchResponse:
    headers = {"x-rapidapi-host": "real-time-amazon-data.p.rapidapi.com", "x-rapidapi-key": RAPIDAPI_KEY}

    params = {
        "query": request.query,
        "page": "1",
        "country": "US",
        "sort_by": "RELEVANCE",
        "product_condition": "ALL",
        "is_prime": "false",
        "deals_and_discounts": "NONE",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://real-time-amazon-data.p.rapidapi.com/search", headers=headers, params=params
        )

        if response.status_code != 200:
            raise Exception(f"Error en la llamada a Amazon API: {response.status_code}")

        raw_response = response.json()
        return AmazonSearchResponse(raw_response)


async def get_product_details(asin: str, country: str = "US") -> Dict[str, Any]:
    headers = {"x-rapidapi-host": "real-time-amazon-data.p.rapidapi.com", "x-rapidapi-key": RAPIDAPI_KEY}

    params = {"asin": asin, "country": country}

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://real-time-amazon-data.p.rapidapi.com/product-details", headers=headers, params=params, timeout=20.0
        )

        if response.status_code != 200:
            raise Exception(f"Error with call Amazon RapidApi: {response.status_code}")

        return response.json()

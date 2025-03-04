import httpx
from app.configurations.config import RAPIDAPI_HOST, RAPIDAPI_KEY
from app.externals.aliexpress.requests.aliexpress_search_request import AliexpressSearchRequest
from app.externals.aliexpress.responses.aliexpress_search_response import AliexpressSearchResponse


async def search_products(data: AliexpressSearchRequest) -> AliexpressSearchResponse:
    endpoint = '/item_search_5'
    url = f"{RAPIDAPI_HOST}{endpoint}"

    headers = {
        'Content-Type': 'application/json',
        'x-rapidapi-key': RAPIDAPI_KEY
    }

    params = {
        'q': data.q,
        'page': str(data.page),
        'sort': data.sort
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            params=params,
            headers=headers
        )
        response.raise_for_status()

        return AliexpressSearchResponse(**response.json())


async def get_item_detail(item_id: str):
    endpoint = '/item_detail_7'
    url = f"{RAPIDAPI_HOST}{endpoint}"

    headers = {
        'Content-Type': 'application/json',
        'x-rapidapi-host': 'aliexpress-datahub.p.rapidapi.com',
        'x-rapidapi-key': RAPIDAPI_KEY
    }

    params = {
        'itemId': item_id
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            params=params,
            headers=headers
        )
        response.raise_for_status()

        return response.json()

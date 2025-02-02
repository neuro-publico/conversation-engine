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

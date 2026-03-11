import httpx

from app.configurations.config import RAPIDAPI_KEY

ALIBABA_RAPIDAPI_HOST = "alibaba-datahub.p.rapidapi.com"
ALIBABA_BASE_URL = f"https://{ALIBABA_RAPIDAPI_HOST}"


async def get_item_detail(item_id: str):
    url = f"{ALIBABA_BASE_URL}/item_detail"
    headers = {
        "x-rapidapi-host": ALIBABA_RAPIDAPI_HOST,
        "x-rapidapi-key": RAPIDAPI_KEY,
    }
    params = {"itemId": item_id}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, headers=headers, timeout=30.0)
        response.raise_for_status()
        return response.json()

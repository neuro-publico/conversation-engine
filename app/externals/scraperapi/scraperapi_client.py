import aiohttp
from typing import Dict, Any

from fastapi import HTTPException

from app.configurations.config import SCRAPERAPI_KEY


class ScraperAPIClient:
    def __init__(self):
        self.api_key = SCRAPERAPI_KEY
        self.base_url = "http://api.scraperapi.com"

    async def get_html(self, url: str, params: Dict[str, Any] = None) -> str:
        default_params = {
            "api_key": self.api_key,
            "url": url,
            "render": "true"
        }

        if params:
            default_params.update(params)

        async with aiohttp.ClientSession() as session:
            async with session.get(self.base_url, params=default_params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise HTTPException(status_code=400, detail=error_text)

                return await response.text()

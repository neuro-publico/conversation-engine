from typing import Any, Dict

import aiohttp
from fastapi import HTTPException

from app.configurations.config import SCRAPERAPI_KEY, URL_SCRAPER_LAMBDA


class ScraperAPIClient:
    def __init__(self):
        self.api_key = SCRAPERAPI_KEY
        self.base_url = "http://api.scraperapi.com"
        self.lambda_url = URL_SCRAPER_LAMBDA

    async def get_html(self, url: str, params: Dict[str, Any] = None) -> str:
        default_params = {"api_key": self.api_key, "url": url}

        if params:
            default_params.update(params)

        async with aiohttp.ClientSession() as session:
            async with session.get(self.base_url, params=default_params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise HTTPException(status_code=400, detail=error_text)

                return await response.text()

    async def get_html_lambda(self, url: str) -> str:
        payload = {"url": url}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.lambda_url, headers={"Content-Type": "application/json"}, json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise HTTPException(status_code=400, detail=f"Error lambda API scraper: {error_text}")

                response_data = await response.json()
                return response_data.get("content", "")

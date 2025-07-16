from typing import Dict, Any

import httpx
from app.scrapers.scraper_interface import ScraperInterface
from fastapi import HTTPException


class CJScraper(ScraperInterface):
    def __init__(self):
        self.webhook_url = "https://n8n.fluxi.co/webhook/cj-search"

    async def scrape_direct(self, html: str) -> Dict[str, Any]:
        return {}

    async def scrape(self, url: str, domain: str = None) -> dict:
        payload = {
            "url_cj": url
        }

        headers = {
            "Content-Type": "application/json"
        }

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    self.webhook_url,
                    headers=headers,
                    json=payload
                )

            if response.status_code == 200:
                return response.json()
            else:
                error_message = f"Failed to get data from CJ Dropshipping: {response.status_code}"
                raise HTTPException(status_code=response.status_code, detail=error_message)

        except HTTPException as he:
            raise he
        except Exception as e:
            error_message = f"Request error to CJ Dropshipping: {str(e)}"
            raise HTTPException(status_code=500, detail=error_message)

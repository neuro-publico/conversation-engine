import re
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from app.externals.mercadolibre.mercadolibre_client import get_product_details
from app.scrapers.scraper_interface import ScraperInterface


class MercadoLibreScraper(ScraperInterface):
    async def scrape_direct(self, html: str) -> Dict[str, Any]:
        return {}

    async def scrape(self, url: str, domain: str = None) -> Dict[str, Any]:
        product_id = self._extract_product_id(url)

        try:
            data = await get_product_details(product_id)

            result = {
                "provider_id": "mercadolibre",
                "external_id": data.get("id", product_id),
                "name": data.get("name", ""),
                "description": self._get_description(data),
                "external_sell_price": self._get_price(data),
                "images": self._get_images(data),
            }

            return {"data": result}

        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error processing MercadoLibre product: {str(e)}")

    def _extract_product_id(self, url: str) -> str:
        patterns = [
            r"/p/(M[A-Z]{2}\d+)",
            r"(M[A-Z]{2}\d+)",
            r"product[_/]?(M[A-Z]{2}\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        raise HTTPException(status_code=400, detail="Product not found - Invalid MercadoLibre URL")

    def _get_description(self, data: Dict[str, Any]) -> str:
        main_features = data.get("main_features", [])
        if main_features:
            return "\n".join(f.get("text", "") for f in main_features if f.get("text"))

        short_desc = data.get("short_description", {})
        if short_desc and short_desc.get("content"):
            return short_desc["content"]

        return ""

    def _get_price(self, data: Dict[str, Any]) -> Optional[float]:
        buy_box = data.get("buy_box_winner")
        if buy_box and isinstance(buy_box, dict):
            return buy_box.get("price")
        return None

    def _get_images(self, data: Dict[str, Any]) -> List[str]:
        pictures = data.get("pictures", [])
        return [pic["url"] for pic in pictures if pic.get("url")]

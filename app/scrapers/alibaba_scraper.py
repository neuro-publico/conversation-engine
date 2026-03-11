import re
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from app.externals.alibaba.alibaba_client import get_item_detail
from app.scrapers.scraper_interface import ScraperInterface


class AlibabaScraper(ScraperInterface):
    async def scrape_direct(self, html: str) -> Dict[str, Any]:
        return {}

    async def scrape(self, url: str, domain: str = None) -> Dict[str, Any]:
        item_id = self._extract_item_id(url)
        product_details = await get_item_detail(item_id)

        try:
            item = self._get_item(product_details)

            response = {
                "provider_id": "alibaba",
                "external_id": item_id,
                "name": item.get("title", ""),
                "description": self._get_description(item),
                "external_sell_price": self._get_price(item),
                "images": self._get_images(item),
                "variants": [],
            }

            return {"data": response}

        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error procesando datos del producto: {str(e)}")

    def _extract_item_id(self, url: str) -> str:
        # Format: /product-detail/name_1601120437487.html
        match = re.search(r"_(\d{10,})\.", url)
        if match:
            return match.group(1)

        # Format: itemId=1601120437487
        match = re.search(r"itemId=(\d+)", url)
        if match:
            return match.group(1)

        # Format: /product/1601120437487
        match = re.search(r"/(\d{10,})", url)
        if match:
            return match.group(1)

        raise HTTPException(status_code=400, detail=f"No se pudo extraer el ID del producto de la URL: {url}")

    def _get_item(self, response: Dict[str, Any]) -> Dict[str, Any]:
        item = response.get("result", {}).get("item", {})
        if not item:
            raise ValueError("No se encontraron datos del producto en la respuesta")
        return item

    def _get_description(self, item: Dict[str, Any]) -> str:
        props = item.get("properties", {}).get("list", [])
        if props:
            return "\n".join(f"{p.get('name', '')} {p.get('value', '')}" for p in props)
        return ""

    def _get_price(self, item: Dict[str, Any]) -> Optional[Decimal]:
        try:
            price_list = item["sku"]["def"]["priceModule"]["priceList"]
            if price_list:
                return Decimal(str(price_list[0]["price"]))
        except (KeyError, TypeError, InvalidOperation):
            pass
        return None

    def _get_images(self, item: Dict[str, Any]) -> List[str]:
        images = item.get("images", [])
        return [f"https:{img}" if img.startswith("//") else img for img in images]

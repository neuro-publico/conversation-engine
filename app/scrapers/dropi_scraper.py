import re
from decimal import Decimal
from typing import Dict, Any, List, Optional

from fastapi import HTTPException

from app.externals.dropi.dropi_client import get_product_details
from app.scrapers.helper_price import parse_price
from app.scrapers.scraper_interface import ScraperInterface
from app.configurations.config import DROPI_S3_BASE_URL


class DropiScraper(ScraperInterface):
    async def scrape_direct(self, html: str) -> Dict[str, Any]:
        return {}

    async def scrape(self, url: str, domain: str = None) -> Dict[str, Any]:
        product_id = self._extract_product_id(url)

        try:
            data = await get_product_details(product_id)
            product_data = self._get_product_data(data)

            result = {
                "name": self._get_name(product_data),
                "description": self._get_description(product_data),
                "external_sell_price": self._get_price(product_data),
                "images": self._get_images(product_data),
            }

            variants = self._extract_variants(product_data)
            if variants:
                result["variants"] = variants

            response = {
                "provider_id": "dropi",
                "external_id": product_id,
                **result
            }

            return {"data": response}

        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Error processing product data from Dropi: {str(e)}"
            )

    def _get_product_data(self, response: Dict[str, Any]) -> Dict[str, Any]:
        if not response.get("isSuccess"):
            raise ValueError("Dropi API returned an error.")

        product_data = response.get("objects")
        if not product_data or not isinstance(product_data, dict):
            raise ValueError("No product data found in Dropi response")
        return product_data

    def _get_name(self, product_data: Dict[str, Any]) -> str:
        return product_data.get("name", "")

    def _get_description(self, product_data: Dict[str, Any]) -> str:
        html_description = product_data.get("description", "")
        if not html_description:
            return ""

        # Remove HTML tags for a cleaner description
        clean_text = re.sub(r'<[^>]+>', ' ', html_description)
        # Replace <br> with newlines and clean up whitespace
        clean_text = clean_text.replace('<br>', '\n').strip()
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        return clean_text

    def _get_price(self, product_data: Dict[str, Any]) -> Optional[Decimal]:
        price_str = product_data.get("sale_price")
        if not price_str:
            return None
        return parse_price(price_str)

    def _get_images(self, product_data: Dict[str, Any]) -> List[str]:
        photos = product_data.get("photos", [])
        if not photos:
            return []

        images = []
        for item in photos:
            if item.get("urlS3"):
                images.append(DROPI_S3_BASE_URL + item["urlS3"])
        return images

    def _extract_variants(self, product_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        variations = product_data.get("variations", [])
        if not variations:
            return []
        return []

    def _extract_product_id(self, url: str) -> str:
        match = re.search(r'/product-details/(\d+)', url)
        if match:
            return match.group(1)

        raise HTTPException(
            status_code=400,
            detail="Product ID not found in Dropi URL"
        ) 
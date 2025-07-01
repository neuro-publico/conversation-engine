from fastapi import HTTPException

from app.scrapers.helper_price import parse_price
from app.scrapers.scraper_interface import ScraperInterface
from typing import Dict, Any, List, Optional
import re
from app.externals.amazon.amazon_client import get_product_details
from decimal import Decimal
from typing import Dict, Any


class AmazonScraper(ScraperInterface):
    async def scrape_direct(self, html: str) -> Dict[str, Any]:
        return {}

    async def scrape(self, url: str, domain: str = None) -> Dict[str, Any]:
        asin = self._extract_asin(url)

        try:
            data = await get_product_details(asin)
            product_data = self._get_product_data(data)

            result = {
                "name": self._get_name(product_data),
                "description": self._get_description(product_data),
                "external_sell_price": self._get_price(product_data),
                "images": self._get_images(product_data)
            }

            variants = self._extract_variants(product_data)
            if variants:
                result["variants"] = variants

            response = {
                "provider_id": "amazon",
                "external_id": asin,
                **result
            }

            return {"data": response}

        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Error processing product data: {str(e)}"
            )

    def _get_product_data(self, response: Dict[str, Any]) -> Dict[str, Any]:
        product_data = response.get("data", {})
        if not product_data:
            raise ValueError("No product data found in response")
        return product_data

    def _get_name(self, product_data: Dict[str, Any]) -> str:
        return product_data.get("product_title", product_data.get("title", ""))

    def _get_description(self, product_data: Dict[str, Any]) -> str:
        description = product_data.get("product_description", "")

        if not description:
            about_product = product_data.get("about_product", [])
            if about_product:
                description = "\n".join(about_product)

        return description

    def _get_price(self, product_data: Dict[str, Any]) -> Optional[Decimal]:
        price_str = product_data.get("product_price", "")
        if not price_str:
            price_info = product_data.get("pricing", {})
            price_str = price_info.get("current_price", "")

        if not price_str:
            return None

        return parse_price(price_str)

    def _get_images(self, product_data: Dict[str, Any]) -> List[str]:
        images = []

        product_photos = product_data.get("product_photos", [])
        if product_photos:
            return product_photos

        main_image = product_data.get("product_photo", product_data.get("main_image", ""))
        if main_image:
            images.append(main_image)

        additional_images = product_data.get("images", [])
        if additional_images:
            images.extend(additional_images)

        return images

    def _extract_asin(self, url: str) -> str:
        patterns = [
            r'/dp/([A-Z0-9]{10})',
            r'/gp/product/([A-Z0-9]{10})',
            r'/ASIN/([A-Z0-9]{10})',
            r'asin=([A-Z0-9]{10})',
            r'asin%3D([A-Z0-9]{10})'
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        raise HTTPException(
            status_code=400,
            detail="Product not found - Invalid Amazon URL"
        )

    def _extract_variants(self, product_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        dimensions = product_data.get("product_variations_dimensions", [])
        variations = product_data.get("product_variations", {})
        all_variations = product_data.get("all_product_variations", {})

        if not dimensions or not variations or not all_variations:
            return []

        variants = []
        product_title = product_data.get("product_title", "")

        for asin, variant_data in all_variations.items():
            variant_attributes = self._get_variant_attributes(dimensions, variant_data)
            variant_key = "-".join([attr["value"] for attr in variant_attributes])

            variant_info = {
                "provider_id": "amazon",
                "external_id": asin,
                "name": product_title,
                "images": self._get_variant_images(dimensions, variations, variant_data, product_data),
                "variant_key": variant_key,
                "attributes": variant_attributes
            }

            variants.append(variant_info)

        return variants

    def _get_variant_attributes(self, dimensions: List[str], variant_data: Dict[str, str]) -> List[Dict[str, str]]:
        attributes = []

        for dim in dimensions:
            if dim in variant_data:
                attributes.append({
                    "category_name": dim.capitalize(),
                    "value": variant_data[dim]
                })

        return attributes

    def _get_variant_images(self, dimensions: List[str], variations: Dict[str, List],
                            variant_data: Dict[str, str], product_data: Dict[str, Any]) -> List[str]:
        images = []
        for dim in dimensions:
            if dim in variations and dim in variant_data:
                for var in variations[dim]:
                    if var.get("value") == variant_data.get(dim) and "photo" in var:
                        images.append(var["photo"])
                        break

        if not images:
            main_image = product_data.get("product_photo")
            if main_image:
                images.append(main_image)

        return images

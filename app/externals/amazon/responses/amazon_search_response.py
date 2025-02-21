from dataclasses import dataclass
from typing import List, Optional


@dataclass
class AmazonProduct:
    asin: str
    title: str
    price: float
    image_url: str
    product_url: str


class AmazonSearchResponse:
    def __init__(self, raw_response: dict):
        self.raw_response = raw_response

    def get_products(self) -> List[dict]:
        products = []
        
        for item in self.raw_response.get('data', {}).get('products', []):
            price = self._format_price(item.get('product_price'))
            if price is not None:
                product = {
                    "source": "amazon",
                    "external_id": item.get('asin', ''),
                    "name": item.get('product_title', ''),
                    "url_website": item.get('product_url', ''),
                    "url_image": item.get('product_photo', ''),
                    "price": price
                }
                products.append(product)

        return products

    def _format_price(self, price) -> Optional[float]:
        if not price:
            return None
        try:
            return float(str(price).replace('$', '').replace(',', ''))
        except (ValueError, TypeError):
            return None

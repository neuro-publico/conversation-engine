import json
import logging
import os
from datetime import datetime
from typing import Any, Dict

from json_repair import repair_json

from app.configurations.config import SCRAPER_AGENT, SCRAPER_AGENT_DIRECT
from app.externals.scraperapi.scraperapi_client import ScraperAPIClient
from app.helpers.escape_helper import extract_product_content
from app.pdf.helpers import clean_json, clean_text
from app.requests.message_request import MessageRequest
from app.scrapers.helper_price import parse_price
from app.scrapers.scraper_interface import ScraperInterface
from app.services.message_service_interface import MessageServiceInterface

logger = logging.getLogger(__name__)


class IAScraper(ScraperInterface):
    async def scrape_direct(self, html: str) -> Dict[str, Any]:
        product_content = extract_product_content(html)
        logger.info(f"scrape_direct: extracted content length={len(product_content)} chars")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"simplified_html_{timestamp}.html"

        os.makedirs("scraped_html", exist_ok=True)

        filepath = os.path.join("scraped_html", filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(product_content)

        logger.info(f"HTML simplificado guardado en: {filepath}")

        message_request = MessageRequest(
            query=f"Product content: {product_content} ",
            agent_id=SCRAPER_AGENT_DIRECT,
            conversation_id="",
            json_parser={"code": "string"},
        )

        """ json_parser={
                "products": [
                    {
                        "id": "string",
                        "title": "string",
                        "description": "string",
                        "price": 0,
                        "images": ["string"],
                        "product_url": "string",
                        "variants": [
                            {
                                "title": "string",
                                "price": 0
                            }
                        ]
                    }
                ]
           """

        result = await self.message_service.handle_message_json(message_request)

        return result

    def __init__(self, message_service: MessageServiceInterface):
        self.message_service = message_service

    async def scrape(self, url: str, domain: str = None) -> Dict[str, Any]:
        client = ScraperAPIClient()
        html_content = await client.get_html_lambda(url)
        product_content = extract_product_content(html_content)
        logger.info(f"scrape: url={url} extracted content length={len(product_content)} chars")

        message_request = MessageRequest(
            query=f"provider_id={domain} . product_url={url} Product content: {product_content} ",
            agent_id=SCRAPER_AGENT,
            conversation_id="",
        )

        result = await self.message_service.handle_message(message_request)
        data_clean = clean_text(clean_json(result["text"]))
        try:
            data = json.loads(data_clean)
        except json.JSONDecodeError:
            data = json.loads(repair_json(data_clean))
        if "external_sell_price" in data.get("data", {}):
            data["data"]["external_sell_price"] = parse_price(data["data"]["external_sell_price"])
        images = data["data"].get("images", [])
        cleaned_images = [f"https:{img}" if img.startswith("//") else img for img in images]
        data["data"]["images"] = cleaned_images

        if "variants" in data["data"]:
            data["data"]["variants"] = [
                variant for variant in data["data"]["variants"] if variant.get("variant_key") != "unknown"
            ]

        return data

from app.configurations.config import SCRAPER_AGENT
from app.helpers.escape_helper import clean_html_deeply
from app.pdf.helpers import clean_text, clean_json
from app.requests.message_request import MessageRequest
from app.scrapers.helper_price import parse_price
from app.scrapers.scraper_interface import ScraperInterface
from typing import Dict, Any
from app.externals.scraperapi.scraperapi_client import ScraperAPIClient
from app.services.message_service_interface import MessageServiceInterface
import json


class IAScraper(ScraperInterface):
    def __init__(self, message_service: MessageServiceInterface):
        self.message_service = message_service

    async def scrape(self, url: str, domain: str = None) -> Dict[str, Any]:
        client = ScraperAPIClient()
        html_content = await client.get_html_lambda(url)
        simplified_html_clean = clean_html_deeply(html_content)

        message_request = MessageRequest(
            query=f"provider_id={domain} . product_url={url} Product content: {simplified_html_clean} ",
            agent_id=SCRAPER_AGENT,
            conversation_id="",
        )

        result = await self.message_service.handle_message(message_request)
        data_clean = clean_text(clean_json(result['text']))
        data = json.loads(data_clean)
        data['data']['external_sell_price'] = parse_price(data['data']['external_sell_price'])
        images = data['data'].get('images', [])
        cleaned_images = [
            f"https:{img}" if img.startswith("//") else img for img in images
        ]
        data['data']['images'] = cleaned_images

        if 'variants' in data['data']:
            data['data']['variants'] = [
                variant for variant in data['data']['variants']
                if variant.get('variant_key') != 'unknown'
            ]

        return data

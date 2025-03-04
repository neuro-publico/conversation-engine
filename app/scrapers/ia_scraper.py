from app.configurations.config import SCRAPER_AGENT
from app.pdf.helpers import clean_text, clean_json
from app.requests.message_request import MessageRequest
from app.scrapers.helper_price import parse_price
from app.scrapers.scraper_interface import ScraperInterface
from typing import Dict, Any
from app.externals.scraperapi.scraperapi_client import ScraperAPIClient
from bs4 import BeautifulSoup
from app.services.message_service_interface import MessageServiceInterface
import json


class IAScraper(ScraperInterface):
    def __init__(self, message_service: MessageServiceInterface):
        self.message_service = message_service

    async def scrape(self, url: str, domain: str = None) -> Dict[str, Any]:
        client = ScraperAPIClient()
        html_content = await client.get_html(url)
        soup = BeautifulSoup(html_content, 'html.parser')
        for script in soup(["script", "style"]):
            script.extract()
        simplified_html = str(soup)

        message_request = MessageRequest(
            query=f"provider_id={domain} . Product content: {simplified_html} ",
            agent_id=SCRAPER_AGENT,
            conversation_id="",
        )

        result = await self.message_service.handle_message(message_request)
        data_clean = clean_text(clean_json(result['text']))
        data = json.loads(data_clean)
        data['data']['external_sell_price'] = parse_price(data['data']['external_sell_price'])
        
        if 'variants' in data['data']:
            filtered_variants = []
            for variant in data['data']['variants']:
                if not (variant.get('name') == 'unknown' and 
                        variant.get('variant_key') == 'unknown' and 
                        len(variant.get('images', [])) == 0):
                    filtered_variants.append(variant)
            
            data['data']['variants'] = filtered_variants

        return data
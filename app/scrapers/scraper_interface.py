from abc import ABC, abstractmethod
from typing import Dict, Any


class ScraperInterface(ABC):
    @abstractmethod
    async def scrape(self, url: str, domain: str = None) -> Dict[str, Any]:
        pass

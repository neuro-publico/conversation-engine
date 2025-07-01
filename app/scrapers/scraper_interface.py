from abc import ABC, abstractmethod
from typing import Dict, Any


class ScraperInterface(ABC):
    @abstractmethod
    async def scrape(self, url: str, domain: str = None) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def scrape_direct(self, html: str) -> Dict[str, Any]:
        """
        Optional method to scrape directly from HTML content.
        This can be overridden by subclasses if needed.
        """
        raise NotImplementedError("This method is not implemented.")
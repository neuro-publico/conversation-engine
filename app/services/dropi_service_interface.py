from abc import ABC, abstractmethod
from typing import Any, Dict, List


class DropiServiceInterface(ABC):
    @abstractmethod
    async def get_departments(self, country: str = "co") -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def get_cities_by_department(self, department_id: int, country: str = "co") -> List[Dict[str, Any]]:
        pass

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class DropiServiceInterface(ABC):
    @abstractmethod
    async def get_departments(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def get_cities_by_department(self, department_id: int) -> List[Dict[str, Any]]:
        pass 
from typing import Any, Dict, List

from fastapi import Depends, HTTPException

from app.externals.dropi import dropi_client
from app.services.dropi_service_interface import DropiServiceInterface


class DropiService(DropiServiceInterface):
    def __init__(self):
        pass

    async def get_departments(self, country: str = "co") -> List[Dict[str, Any]]:
        try:
            response = await dropi_client.get_departments(country)
            return response.get("objects", [])
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching departments from Dropi: {str(e)}")

    async def get_cities_by_department(self, department_id: int, country: str = "co") -> List[Dict[str, Any]]:
        try:
            rate_type = "CON RECAUDO"
            response = await dropi_client.get_cities_by_department(department_id, rate_type, country)
            return response.get("objects", {}).get("cities", [])
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching cities from Dropi: {str(e)}")

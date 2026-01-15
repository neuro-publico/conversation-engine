from functools import wraps
from typing import Optional

import httpx
from fastapi import Header, HTTPException, Request

from app.configurations.config import API_KEY, AUTH_SERVICE_URL


async def verify_api_key(api_key: Optional[str]) -> bool:
    if not api_key:
        raise HTTPException(status_code=401, detail="API Key not provided")

    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")

    return True


def require_api_key(func):
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        if request is None:
            raise HTTPException(status_code=500, detail="Request not found")
        await verify_api_key(request.headers.get("x-api-key"))
        return await func(request, *args, **kwargs)

    return wrapper


async def verify_user_token(authorization: Optional[str]) -> dict:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization token not provided")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(AUTH_SERVICE_URL, headers={"Authorization": authorization}, timeout=3.0)

            if response.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid token")

            return response.json()
    except httpx.RequestError:
        raise HTTPException(status_code=500, detail="Error verifying token")


def require_auth(func):
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        if request is None:
            raise HTTPException(status_code=500, detail="Request not found")
        user_info = await verify_user_token(request.headers.get("authorization"))
        request.state.user_info = user_info
        return await func(request, *args, **kwargs)

    return wrapper

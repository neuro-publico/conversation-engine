import httpx

from app.configurations.config import HOST_AGENT_CONFIG
from app.externals.agent_config.requests.agent_config_request import AgentConfigRequest
from app.externals.agent_config.responses.agent_config_response import AgentConfigResponse


async def get_agent(data: AgentConfigRequest) -> AgentConfigResponse:
    endpoint = '/api/ms/agent/config/search-agent'
    url = f"{HOST_AGENT_CONFIG}{endpoint}"
    headers = {'Content-Type': 'application/json'}

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data.model_dump(), headers=headers)
        response.raise_for_status()

        return AgentConfigResponse(**response.json())

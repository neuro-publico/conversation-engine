from typing import Optional, Dict, List
from pydantic import BaseModel


class AgentPreferences(BaseModel):
    temperature: float
    max_tokens: int
    top_p: float


class Property(BaseModel):
    name: str
    description: str


class Config(BaseModel):
    properties: List[Property]
    name: str
    description: str
    api: str
    method: str
    body: Dict[str, str]
    headers: List[Dict[str, str]]
    query_params: Optional[Dict[str, str]]


class Tool(BaseModel):
    tool_id: int
    tool_name: str
    description: str
    config: Config


class AgentMetadata(BaseModel):
    base_prompt: bool


class AgentConfigResponse(BaseModel):
    id: int
    agent_id: str
    description: str
    prompt: str
    provider_ai: str
    model_ai: str
    preferences: AgentPreferences

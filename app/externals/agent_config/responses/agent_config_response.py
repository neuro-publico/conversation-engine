from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field


class AgentPreferences(BaseModel):
    temperature: float = 0.7
    max_tokens: int = 1000
    top_p: float = 1.0


class Property(BaseModel):
    name: str
    description: str


class Config(BaseModel):
    properties: List[Property]
    name: str
    description: str
    api: str
    method: str
    body: Optional[Dict[str, str]]
    headers: Optional[List[Dict[str, str]]]
    query_params: Optional[Dict[str, str]]


class Tool(BaseModel):
    id: int
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
    tools: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    mcp_config: Optional[Dict[str, Any]] = None

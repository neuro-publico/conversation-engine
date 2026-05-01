from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentPreferences(BaseModel):
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    extra_parameters: Optional[Dict[str, Any]] = None
    # Phase 2 V3 (Apr 18 2026) — per-agent Gemini thinking budget.
    # One of: "High" | "Medium" | "Low" | "None" | null. None/null disables
    # thinking (recommended for creative-writing-heavy agents where the
    # model over-deliberates and produces flat outputs). High stays default
    # for reasoning-heavy agents (UGC ad analysis, script validators).
    # Only Gemini preview/flash models honor this — other models ignore it.
    thinking_level: Optional[str] = None


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
    metadata: Optional[Dict[str, Any]] = None

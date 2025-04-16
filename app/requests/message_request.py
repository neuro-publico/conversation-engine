from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class MessageRequest(BaseModel):
    agent_id: str
    conversation_id: str
    query: str
    metadata_filter: Optional[Dict[str, Any]] = Field(default_factory=dict)
    parameter_prompt: Optional[Dict[str, Any]] = Field(default_factory=dict)
    files: Optional[List[Dict[str, str]]] = Field(default_factory=list)
    json_parser: Optional[Dict[str, Any]] = None

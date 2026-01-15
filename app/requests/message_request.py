from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MetadataFilter(BaseModel):
    key: str
    value: str
    evaluator: str = "="


class MessageRequest(BaseModel):
    agent_id: str
    conversation_id: str
    query: str
    metadata_filter: Optional[List[MetadataFilter]] = Field(default_factory=list)
    parameter_prompt: Optional[Dict[str, Any]] = Field(default_factory=dict)
    files: Optional[List[Dict[str, str]]] = Field(default_factory=list)
    json_parser: Optional[Dict[str, Any]] = None

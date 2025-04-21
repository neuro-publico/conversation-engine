from typing import List, Dict, Optional, Any
from pydantic import BaseModel

from app.requests.message_request import MetadataFilter


class AgentConfigRequest(BaseModel):
    agent_id: Optional[str] = None
    query: str
    metadata_filter: Optional[List[MetadataFilter]] = None
    parameter_prompt: Optional[Dict[str, Any]] = None

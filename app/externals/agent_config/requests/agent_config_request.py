from typing import List, Dict, Optional, Any
from pydantic import BaseModel


class AgentConfigRequest(BaseModel):
    agent_id: Optional[str] = None
    query: str
    metadata_filter: Optional[List[Dict[str, str]]] = None
    parameter_prompt: Optional[Dict[str, Any]] = None

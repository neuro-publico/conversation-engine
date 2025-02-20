from pydantic import BaseModel
from typing import Optional, List, Dict


class MessageRequest(BaseModel):
    agent_id: Optional[str]
    query: str
    conversation_id: str
    metadata_filter: Optional[dict] = None
    parameter_prompt: Optional[dict] = None
    files: Optional[List[Dict[str, str]]] = None

from typing import Dict, Any, List, Optional
from app.processors.conversation_processor import ConversationProcessor
from app.requests.message_request import MessageRequest
from langchain_core.language_models import BaseChatModel
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
import json
import re


class MCPProcessor(ConversationProcessor):
    def __init__(self, llm: BaseChatModel, context: str, history: List[str], mcp_config: Dict[str, Any]):
        super().__init__(llm, context, history)
        self.mcp_config = mcp_config

    async def process(self, request: MessageRequest, files: Optional[List[Dict[str, str]]] = None,
                      supports_interleaved_files: bool = False) -> Dict[str, Any]:
        async with MultiServerMCPClient(self.mcp_config) as client:
            agent = create_react_agent(self.llm, client.get_tools())

            system_message = self.context or ""
            if request.json_parser:
                format_instructions = json.dumps(request.json_parser, indent=2)
                system_message += (
                    "\n\nIMPORTANT: Respond exclusively in JSON format following exactly this structure:\n\n"
                    f"{format_instructions}\n\n"
                    "Do NOT include markdown, explanations, or anything else besides the JSON."
                )

            messages = []
            if system_message:
                messages.append({"role": "system", "content": system_message})

            if self.history:
                messages.extend(self.history)

            messages.append({"role": "user", "content": request.query})

            config = self._get_langsmith_config(
                request,
                "mcp_processor",
                mcp_servers=list(self.mcp_config.keys()) if isinstance(self.mcp_config, dict) else []
            )

            response = await agent.ainvoke({"messages": messages}, config=config)

            content = ""
            if "messages" in response and response["messages"]:
                last_message = response["messages"][-1]
                if hasattr(last_message, "content"):
                    content = last_message.content
                elif isinstance(last_message, dict) and "content" in last_message:
                    content = last_message["content"]
                else:
                    content = str(last_message)
            else:
                content = str(response)

            match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
            result = match.group(1) if match else content

            tool_info = await self.get_tool_data(response)

            return {
                "context": self.context,
                "chat_history": self.history,
                "input": request.query,
                "text": result,
                "tool_result": tool_info
            }

    async def get_tool_data(self, response):
        tool_messages = [
            msg for msg in response.get('messages', [])
            if getattr(msg, 'type', None) == 'tool'
        ]
        tool_info = None
        if tool_messages:
            last_tool = tool_messages[-1]
            name = last_tool.name
            tool_result = last_tool.content
            try:
                tool_result_json = json.loads(tool_result)
            except json.JSONDecodeError:
                tool_result_json = tool_result

            tool_info = {
                "name": name,
                "message": tool_result_json
            }
        return tool_info

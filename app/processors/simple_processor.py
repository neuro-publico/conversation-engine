import json
from typing import Dict, Any, Optional, List
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.processors.conversation_processor import ConversationProcessor
from app.requests.message_request import MessageRequest
import re


class SimpleProcessor(ConversationProcessor):
    async def generate_response(self, context: str, chat_history: list, query: str, prompt: ChatPromptTemplate, 
                                config: dict = None) -> Dict[str, Any]:
        chain = (
                {
                    "context": lambda x: x["context"],
                    "chat_history": lambda x: x["chat_history"],
                    "input": lambda x: x["input"],
                }
                | prompt
                | self.llm
        )

        raw_response = await chain.ainvoke({
            "context": context,
            "chat_history": chat_history,
            "input": query
        }, config=config)

        content = raw_response.content

        match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
        if match:
            json_content = match.group(1)
            response_content = json_content
        else:
            response_content = content

        return {
            "context": context,
            "chat_history": chat_history,
            "input": query,
            "text": response_content
        }

    async def process(self, request: MessageRequest, files: Optional[List[Dict[str, str]]] = None,
                      supports_interleaved_files: bool = False) -> Dict[str, Any]:
        messages = []
        system_message = self.context or ""

        if files and not supports_interleaved_files:
            file_references = []
            for file in files:
                tag = 'image' if file.get('type') == 'image' else 'file'
                file_references.append(f"<{tag} url='{file['url']}'></{tag}>")

            system_message += "\n\n" + "\n".join(file_references)

        if request.json_parser:
            format_instructions = json.dumps(request.json_parser, indent=2)
            system_message += (
                "\n\nIMPORTANT: Respond exclusively in JSON format following exactly this structure:\n\n"
                f"{format_instructions}\n\n"
                "Do NOT include markdown, explanations, or anything else besides the JSON."
            )

        if files and supports_interleaved_files:
            interleaved_references = []
            for file in files:
                tag = 'image' if file.get('type') == 'image' else 'file'
                interleaved_references.append(f"<{tag} url='{file['url']}'></{tag}>")
            system_message += "\n\n" + "\n".join(interleaved_references)

        messages.append(SystemMessage(content=system_message))
        messages.append(MessagesPlaceholder(variable_name="chat_history"))
        messages.append(HumanMessage(content=request.query))

        prompt = ChatPromptTemplate.from_messages(messages)
        
        config = self._get_langsmith_config(
            request,
            "simple_processor",
            has_json_parser=request.json_parser is not None,
            has_files=files is not None and len(files) > 0
        )
        
        return await self.generate_response(self.context, self.history, request.query, prompt, config)

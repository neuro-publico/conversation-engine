import json
import re
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.processors.conversation_processor import ConversationProcessor
from app.requests.message_request import MessageRequest


class SimpleProcessor(ConversationProcessor):
    async def generate_response(
        self, context: str, chat_history: list, query: str, prompt: ChatPromptTemplate, config: dict = None
    ) -> Dict[str, Any]:
        chain = (
            {
                "context": lambda x: x["context"],
                "chat_history": lambda x: x["chat_history"],
                "input": lambda x: x["input"],
            }
            | prompt
            | self.llm
        )

        raw_response = await chain.ainvoke(
            {"context": context, "chat_history": chat_history, "input": query}, config=config
        )

        content = raw_response.content

        match = re.search(r"```json\n(.*?)\n```", content, re.DOTALL)
        if match:
            json_content = match.group(1)
            response_content = json_content
        else:
            response_content = content

        return {"context": context, "chat_history": chat_history, "input": query, "text": response_content}

    async def process(
        self,
        request: MessageRequest,
        files: Optional[List[Dict[str, str]]] = None,
        supports_interleaved_files: bool = False,
    ) -> Dict[str, Any]:
        messages = []
        system_message = self.context or ""

        if files and not supports_interleaved_files:
            file_references = []
            for file in files:
                tag = "image" if file.get("type") == "image" else "file"
                file_references.append(f"<{tag} url='{file['url']}'></{tag}>")

            system_message += "\n\n" + "\n".join(file_references)

        if request.json_parser:
            format_instructions = json.dumps(request.json_parser, indent=2)
            system_message += (
                "\n\nIMPORTANT: Respond exclusively in JSON format following exactly this structure:\n\n"
                f"{format_instructions}\n\n"
                "Do NOT include markdown, explanations, or anything else besides the JSON."
            )

        messages.append(SystemMessage(content=system_message))
        messages.append(MessagesPlaceholder(variable_name="chat_history"))

        # Si hay archivos y el provider soporta content blocks, enviarlos correctamente
        if files and supports_interleaved_files:
            # Incluir las URLs como texto para que el modelo las tenga como referencia
            image_urls = [file["url"] for file in files if file.get("type") == "image" and file.get("url")]
            query_with_urls = request.query
            if image_urls:
                urls_list = "\n".join([f"{i+1}. {url}" for i, url in enumerate(image_urls)])
                query_with_urls += f"\n\nIMPORTANT: You must respond with ONE of these exact URLs, do not invent or modify URLs:\n{urls_list}"

            content_blocks = [{"type": "text", "text": query_with_urls}]
            for file in files:
                file_type = file.get("type", "file")
                if file_type == "image":
                    # Formato OpenAI: type=image_url con nested image_url.url
                    content_blocks.append({"type": "image_url", "image_url": {"url": file["url"]}})
                else:
                    content_blocks.append({"type": "file", "url": file["url"]})
            messages.append(HumanMessage(content=content_blocks))
        else:
            messages.append(HumanMessage(content=request.query))

        prompt = ChatPromptTemplate.from_messages(messages)

        config = self._get_langsmith_config(
            request,
            "simple_processor",
            has_json_parser=request.json_parser is not None,
            has_files=files is not None and len(files) > 0,
        )

        return await self.generate_response(self.context, self.history, request.query, prompt, config)

from typing import Dict, Any, Optional, List, Union
from langchain.chains import LLMChain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from app.processors.conversation_processor import ConversationProcessor


class SimpleProcessor(ConversationProcessor):
    async def process(self, query: str, files: Optional[List[Dict[str, str]]] = None, supports_interleaved_files: bool = False) -> Dict[str, Any]:
        messages = []
        system_message = self.context or ""

        if files and not supports_interleaved_files:
            file_references = []
            for file in files:
                if file.get('type') == 'image':
                    file_references.append(f"<image>{file['url']}</image>")
                else:
                    file_references.append(f"<file url='{file['url']}'></file>")

            system_message += "\n\n" + "\n".join(file_references)

        messages.append(("system", system_message))
        messages.append(MessagesPlaceholder(variable_name="chat_history"))

        if files and supports_interleaved_files:
            for file in files:
                if file.get('type') == 'image':
                    messages.append(("system", f"<image>{file['url']}</image>"))
                else:
                    messages.append(("system", f"<file url='{file['url']}'></file>"))

        messages.append(("human", query))
        prompt = ChatPromptTemplate.from_messages(messages)

        chain = LLMChain(
            llm=self.llm,
            prompt=prompt,
            verbose=False
        )

        return await chain.ainvoke({
            "context": self.context or "",
            "chat_history": self.history,
            "input": query
        })

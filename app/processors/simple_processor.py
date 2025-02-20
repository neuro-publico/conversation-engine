from typing import Dict, Any, Optional, List, Union
from langchain.chains import LLMChain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from app.processors.conversation_processor import ConversationProcessor


class SimpleProcessor(ConversationProcessor):
    async def process(self, query: str, files: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        messages = [
            ("system", "{context}"),
            MessagesPlaceholder(variable_name="chat_history")
        ]

        if files:
            for file in files:
                if file.get('type') == 'image':
                    messages.append(("system", f"<image>{file['content']}</image>"))
                else:
                    messages.append(("system", f"<file>\n{file['path']}\n```{file['content']}```\n</file>"))

        messages.append(("human", "{input}"))
        
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
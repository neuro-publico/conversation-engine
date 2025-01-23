from typing import Dict, Any
from langchain.chains import LLMChain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from app.processors.conversation_processor import ConversationProcessor


class SimpleProcessor(ConversationProcessor):
    async def process(self, query: str) -> Dict[str, Any]:
        prompt = ChatPromptTemplate.from_messages([
            ("system", "{context}"),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}")
        ])

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
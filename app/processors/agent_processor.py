from typing import Dict, Any, List, Optional
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from app.processors.conversation_processor import ConversationProcessor
from langchain_core.language_models import BaseChatModel
import traceback

from app.requests.message_request import MessageRequest


class AgentProcessor(ConversationProcessor):
    def __init__(self, llm: BaseChatModel, context: str, history: List[str], tools: List[Any]):
        super().__init__(llm, context, history)
        self.tools = tools

    async def process(self, request: MessageRequest, files: Optional[List[Dict[str, str]]] = None,
                      supports_interleaved_files: bool = False) -> Dict[str, Any]:
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", "{context}"),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = create_tool_calling_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt_template
        )

        agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=False,
            handle_parsing_errors=True,
            max_iterations=3,
            return_intermediate_steps=True
        )

        try:
            config = self._get_langsmith_config(
                request, 
                "agent_processor",
                has_tools=len(self.tools) > 0
            )
            
            result = await agent_executor.ainvoke({
                "context": self.context or "",
                "chat_history": self.history,
                "input": request.query,
                "agent_scratchpad": ""
            }, config=config)
            
            if "text" not in result and "output" in result:
                result["text"] = result["output"]
                
            return result
        except Exception as e:
            print(f"Error durante la ejecución del agente: {str(e)}")
            print(f"Traceback completo:", traceback.format_exc())
            return {
                "message": "Lo siento, no pude procesar tu solicitud correctamente. Por favor, intenta reformular tu pregunta."
            }

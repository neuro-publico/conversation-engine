import json

from app.configurations.config import AGENT_RECOMMEND_PRODUCTS_ID
from app.externals.agent_config.agent_config_client import get_agent
from app.externals.aliexpress.requests.aliexpress_search_request import AliexpressSearchRequest
from app.requests.message_request import MessageRequest
from app.externals.agent_config.requests.agent_config_request import AgentConfigRequest
from app.requests.recommend_product_request import RecommendProductRequest
from app.responses.recommend_product_response import RecommendProductResponse
from app.services.message_service_interface import MessageServiceInterface
from app.managers.conversation_manager_interface import ConversationManagerInterface
from fastapi import Depends
from app.externals.aliexpress.aliexpress_client import search_products


class MessageService(MessageServiceInterface):
    def __init__(self, conversation_manager: ConversationManagerInterface = Depends()):
        self.conversation_manager = conversation_manager

    async def handle_message(self, request: MessageRequest):
        data = AgentConfigRequest(
            agent_id=request.agent_id,
            query=request.query,
            metadata_filter=request.metadata_filter,
            parameter_prompt=request.parameter_prompt
        )

        agent_config = await get_agent(data)

        return await self.conversation_manager.process_conversation(
            request=request,
            agent_config=agent_config
        )

    async def recommend_products(self, request: RecommendProductRequest):
        data = await self.handle_message(MessageRequest(
            agent_id=AGENT_RECOMMEND_PRODUCTS_ID,
            conversation_id="",
            query=f"Product Name: {request.product_name} Description: {request.product_description}",
        ))

        json_data = json.loads(data['text'])
        aliexpress_data = await search_products(AliexpressSearchRequest(q=json_data['recommended_product']))

        return RecommendProductResponse(ai_response=json_data, products=aliexpress_data.get_products())

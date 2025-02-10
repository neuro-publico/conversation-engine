import json
import uuid
import asyncio

from app.configurations.config import AGENT_RECOMMEND_PRODUCTS_ID
from app.externals.agent_config.agent_config_client import get_agent
from app.externals.aliexpress.requests.aliexpress_search_request import AliexpressSearchRequest
from app.externals.s3_upload.requests.s3_upload_request import S3UploadRequest
from app.externals.s3_upload.s3_upload_client import upload_file
from app.pdf.helpers import clean_text, clean_json
from app.requests.generate_pdf_request import GeneratePdfRequest
from app.requests.message_request import MessageRequest
from app.externals.agent_config.requests.agent_config_request import AgentConfigRequest
from app.requests.recommend_product_request import RecommendProductRequest
from app.responses.recommend_product_response import RecommendProductResponse
from app.services.message_service_interface import MessageServiceInterface
from app.managers.conversation_manager_interface import ConversationManagerInterface
from fastapi import Depends
from app.externals.aliexpress.aliexpress_client import search_products
from app.configurations.pdf_manual_config import PDF_MANUAL_SECTIONS
from app.pdf.pdf_manual_generator import PDFManualGenerator


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

    async def process_multiple_agents(self, agent_queries: list[dict]) -> dict:
        tasks = [
            self.handle_message(MessageRequest(
                agent_id=item['agent'],
                conversation_id="",
                query=item['query']
            )) for item in agent_queries
        ]

        try:
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            combined_data = {}
            for response in responses:
                if isinstance(response, Exception):
                    continue
                data_clean = clean_text(clean_json(response['text']))
                data = json.loads(data_clean)
                combined_data.update(data)

            if not combined_data:
                raise ValueError("No se pudo obtener respuesta válida de ningún agente")

            return combined_data

        except Exception as e:
            raise ValueError(f"Error procesando respuestas de agentes: {str(e)}")

    async def generate_pdf(self, request: GeneratePdfRequest):
        base_query = f"Product Name: {request.product_name} Description: {request.product_description}"

        agent_queries = [
            {'agent': "agent_copies_pdf", 'query': f"section: {section}. {base_query} "}
            for section, _ in PDF_MANUAL_SECTIONS.items()
        ]

        combined_data = await self.process_multiple_agents(agent_queries)

        unique_id = uuid.uuid4().hex[:8]
        file_name = f"{request.product_name.replace(' ', '_').lower()}_{unique_id}"

        pdf_generator = PDFManualGenerator(request.product_name)
        pdf = await pdf_generator.create_manual(combined_data)

        return await upload_file(
            S3UploadRequest(file=pdf, folder=f"{request.owner_id}/pdfs",
                            filename=file_name))

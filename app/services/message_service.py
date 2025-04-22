import json
import asyncio

from app.configurations.config import AGENT_RECOMMEND_PRODUCTS_ID, AGENT_RECOMMEND_SIMILAR_PRODUCTS_ID, ENVIRONMENT
from app.configurations.copies_config import AGENT_COPIES
from app.externals.agent_config.agent_config_client import get_agent
from app.externals.s3_upload.requests.s3_upload_request import S3UploadRequest
from app.externals.s3_upload.s3_upload_client import upload_file, check_file_exists_direct
from app.pdf.helpers import clean_text, clean_json
from app.requests.copy_request import CopyRequest
from app.requests.generate_pdf_request import GeneratePdfRequest
from app.requests.message_request import MessageRequest
from app.externals.agent_config.requests.agent_config_request import AgentConfigRequest
from app.requests.recommend_product_request import RecommendProductRequest
from app.responses.recommend_product_response import RecommendProductResponse
from app.services.message_service_interface import MessageServiceInterface
from app.managers.conversation_manager_interface import ConversationManagerInterface
from fastapi import Depends
from app.configurations.pdf_manual_config import PDF_MANUAL_SECTIONS
from app.pdf.pdf_manual_generator import PDFManualGenerator
from app.externals.amazon.requests.amazon_search_request import AmazonSearchRequest
from app.externals.amazon.amazon_client import search_products


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

    async def handle_message_json(self, request: MessageRequest):
        response = await self.handle_message(request)

        return json.loads(response['text'])

    async def recommend_products(self, request: RecommendProductRequest):
        agent_id = AGENT_RECOMMEND_SIMILAR_PRODUCTS_ID if request.similar else AGENT_RECOMMEND_PRODUCTS_ID

        data = await self.handle_message(MessageRequest(
            agent_id=agent_id,
            conversation_id="",
            query=f"Product Name: {request.product_name} Description: {request.product_description}",
        ))

        json_data = json.loads(data['text'])
        amazon_data = await search_products(AmazonSearchRequest(query=json_data['recommended_product']))

        return RecommendProductResponse(ai_response=json_data, products=amazon_data.get_products())

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

    async def generate_copies(self, request: CopyRequest):
        agent_queries = [
            {'agent': agent, 'query': request.prompt}
            for agent in AGENT_COPIES
        ]

        combined_data = await self.process_multiple_agents(agent_queries)

        return {"copies": combined_data}

    async def generate_pdf(self, request: GeneratePdfRequest):
        base_query = f"Product Name: {request.product_name} Description: {request.product_description}. Language: {request.language}."
        base_filename = f"{request.product_id}_{request.language}"
        version = "v1"
        base_url = f"https://fluxi.co/{ENVIRONMENT}/assets"
        folder_path = f"{request.owner_id}/pdfs/{version}"
        s3_url = f"{base_url}/{folder_path}/{base_filename}.pdf"
        exists = await check_file_exists_direct(s3_url)

        if exists:
            return {"s3_url": s3_url}

        agent_queries = [
            {'agent': "agent_copies_pdf", 'query': f"section: {section}. {base_query} "}
            for section, _ in PDF_MANUAL_SECTIONS.items()
        ]

        combined_data = await self.process_multiple_agents(agent_queries)

        pdf_generator = PDFManualGenerator(request.product_name)
        pdf = await pdf_generator.create_manual(combined_data)

        result = await upload_file(
            S3UploadRequest(
                file=pdf,
                folder=folder_path,
                filename=base_filename
            )
        )

        return result

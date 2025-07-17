import json
import asyncio

from app.configurations.config import AGENT_RECOMMEND_PRODUCTS_ID, AGENT_RECOMMEND_SIMILAR_PRODUCTS_ID, ENVIRONMENT
from app.configurations.copies_config import AGENT_COPIES
from app.externals.agent_config.agent_config_client import get_agent
from app.externals.s3_upload.requests.s3_upload_request import S3UploadRequest
from app.externals.s3_upload.s3_upload_client import upload_file, check_file_exists_direct
from app.pdf.helpers import clean_text, clean_json
from app.requests.brand_context_resolver_request import BrandContextResolverRequest
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
from app.requests.resolve_funnel_request import ResolveFunnelRequest


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

    async def resolve_funnel(self, request: ResolveFunnelRequest):
        pain_detection_response = await self.handle_message(MessageRequest(
            agent_id="pain_detection",
            conversation_id="",
            query="pain_detection",
            parameter_prompt={
                "product_name": request.product_name,
                "product_description": request.product_description
            }
        ))

        pain_detection_message = pain_detection_response['text']

        buyer_detection_response = await self.handle_message(MessageRequest(
            agent_id="buyer_detection",
            conversation_id="",
            query="buyer_detection",
            parameter_prompt={
                "product_name": request.product_name,
                "product_description": request.product_description,
                "pain_detection": pain_detection_message
            }
        ))

        buyer_detection_message = buyer_detection_response['text']

        sales_angles_response = await self.handle_message_json(MessageRequest(
            agent_id="sales_angles_v2",
            conversation_id="",
            query="sales_angles_v2",
            json_parser={
                "angles": [
                    {
                        "name": "string",
                        "description": "string"
                    }
                ]
            },
            parameter_prompt={
                "product_name": request.product_name,
                "product_description": request.product_description,
                "pain_detection": pain_detection_message,
                "buyer_detection": buyer_detection_message
            }
        ))

        return {
            "pain_detection": pain_detection_message,
            "buyer_detection": buyer_detection_message,
            "sales_angles": sales_angles_response["angles"]
        }

    async def resolve_brand_context(self, request: BrandContextResolverRequest):
        brand_agent_task = self.handle_message_json(MessageRequest(
            agent_id="store_brand_agent",
            conversation_id="",
            query="store_brand_agent",
            parameter_prompt=request.prompt,
            json_parser={"brands": ["string", "string"]}
        ))

        context_agent_task = self.handle_message_json(MessageRequest(
            agent_id="store_context_agent",
            conversation_id="",
            query="store_context_agent",
            parameter_prompt=request.prompt,
            json_parser={"contexts": ["string", "string"]}
        ))

        responses = await asyncio.gather(brand_agent_task, context_agent_task)

        brands = responses[0].get("brands", [])
        contexts = responses[1].get("contexts", [])

        return {
            "brands": brands,
            "contexts": contexts
        }

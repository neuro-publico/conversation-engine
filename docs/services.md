# Servicios

Los servicios encapsulan la lógica de negocio principal de la aplicación.

## MessageService

Servicio principal para el procesamiento de mensajes y conversaciones.

### Métodos

#### handle_message

Procesa un mensaje y retorna la respuesta del agente.

```python
async def handle_message(self, request: MessageRequest) -> dict:
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
```

#### handle_message_json

Procesa un mensaje y parsea la respuesta como JSON.

```python
async def handle_message_json(self, request: MessageRequest):
    response = await self.handle_message(request)
    return json.loads(response['text'])
```

#### recommend_products

Recomienda productos basándose en nombre y descripción.

```python
async def recommend_products(self, request: RecommendProductRequest):
    agent_id = AGENT_RECOMMEND_SIMILAR_PRODUCTS_ID if request.similar else AGENT_RECOMMEND_PRODUCTS_ID

    data = await self.handle_message(MessageRequest(
        agent_id=agent_id,
        conversation_id="",
        query=f"Product Name: {request.product_name} Description: {request.product_description}",
    ))

    json_data = json.loads(data['text'])
    amazon_data = await search_products(AmazonSearchRequest(query=json_data['recommended_product']))

    return RecommendProductResponse(
        ai_response=json_data, 
        products=amazon_data.get_products()
    )
```

#### generate_copies

Genera copys de marketing procesando múltiples agentes en paralelo.

```python
async def generate_copies(self, request: CopyRequest):
    agent_queries = [
        {'agent': agent, 'query': request.prompt}
        for agent in AGENT_COPIES
    ]

    combined_data = await self.process_multiple_agents(agent_queries)
    return {"copies": combined_data}
```

#### generate_pdf

Genera un manual PDF para un producto.

```python
async def generate_pdf(self, request: GeneratePdfRequest):
    # Verificar si ya existe
    exists = await check_file_exists_direct(s3_url)
    if exists:
        return {"s3_url": s3_url}

    # Generar secciones con múltiples agentes
    sections = get_sections_for_language(request.language)
    agent_queries = [
        {'agent': "agent_copies_pdf", 'query': f"section: {section}. {base_query}"}
        for section in sections.keys()
    ]

    combined_data = await self.process_multiple_agents(agent_queries)

    # Crear PDF
    pdf_generator = PDFManualGenerator(request.product_name, language=request.language)
    pdf = await pdf_generator.create_manual(combined_data, request.title, request.image_url)

    # Subir a S3
    result = await upload_file(S3UploadRequest(...))
    return result
```

#### resolve_funnel

Genera información de funnel de ventas.

```python
async def resolve_funnel(self, request: ResolveFunnelRequest):
    # 1. Detección de dolor
    pain_detection_response = await self.handle_message(MessageRequest(
        agent_id="pain_detection",
        parameter_prompt={"product_name": ..., "product_description": ..., "language": ...}
    ))

    # 2. Detección de comprador
    buyer_detection_response = await self.handle_message(MessageRequest(
        agent_id="buyer_detection",
        parameter_prompt={"pain_detection": pain_detection_response['text'], ...}
    ))

    # 3. Ángulos de venta
    sales_angles_response = await self.handle_message_json(MessageRequest(
        agent_id="sales_angles_v2",
        json_parser={"angles": [{"name": "string", "description": "string"}]},
        parameter_prompt={...}
    ))

    return {
        "pain_detection": pain_detection_message,
        "buyer_detection": buyer_detection_message,
        "sales_angles": sales_angles_response["angles"]
    }
```

---

## ImageService

Servicio para generación y manipulación de imágenes.

### Métodos

#### generate_variation_images

Genera variaciones de una imagen existente.

```python
async def generate_variation_images(self, request: VariationImageRequest, owner_id: str):
    folder_id = uuid.uuid4().hex[:8]
    
    # Subir imagen original
    original_image_response = await self._upload_to_s3(request.file, owner_id, folder_id, "original")
    
    # Analizar con Google Vision
    vision_analysis = await analyze_image(request.file)

    # Obtener prompt del agente
    message_request = MessageRequest(
        query=f"Attached is the product image. {vision_analysis.get_analysis_text()}",
        agent_id=AGENT_IMAGE_VARIATIONS,
        files=[{"type": "image", "url": original_image_response.s3_url, "content": request.file}]
    )

    response_data = await self.message_service.handle_message_with_config(message_request)
    prompt = response_data["message"]["text"]

    # Generar variaciones en paralelo
    tasks = [
        self._generate_single_variation([original_image_response.s3_url], prompt, owner_id, folder_id, ...)
        for i in range(request.num_variations)
    ]
    generated_urls = await asyncio.gather(*tasks)

    return GenerateImageResponse(
        generated_urls=generated_urls,
        original_url=original_image_response.s3_url,
        generated_prompt=prompt,
        vision_analysis=vision_analysis
    )
```

#### generate_images_from

Genera imágenes desde un prompt y/o imagen base.

```python
async def generate_images_from(self, request: GenerateImageRequest, owner_id: str):
    folder_id = uuid.uuid4().hex[:8]
    
    if request.file:
        original_image_response = await self._upload_to_s3(request.file, ...)
    
    tasks = [
        self._generate_single_variation(urls, request.prompt, owner_id, folder_id, ...)
        for i in range(request.num_variations)
    ]
    generated_urls = await asyncio.gather(*tasks)

    return GenerateImageResponse(
        original_urls=urls,
        generated_urls=generated_urls,
        generated_prompt=request.prompt
    )
```

### Proveedores de Imágenes

```python
async def _generate_single_variation(self, url_images, prompt, owner_id, folder_id, 
                                     provider=None, model_ai=None):
    if provider and provider.lower() == "openai":
        image_content = await openai_image_edit(image_urls=url_images, prompt=prompt, ...)
    else:
        image_content = await google_image(image_urls=url_images, prompt=prompt, ...)
    
    # Comprimir y subir
    content_base64 = base64.b64encode(image_content).decode('utf-8')
    return await self._upload_to_s3(content_base64, owner_id, folder_id, "variation")
```

---

## VideoService

Servicio para generación de videos con FAL AI.

### Tipos de Video

| Tipo | Descripción | Campos requeridos |
|------|-------------|-------------------|
| `animated_scene` | Escena animada desde imagen | prompt, image_url |
| `human_scene` | Escena con humano hablando | image_url, audio_url |

### Implementación

```python
class VideoService(VideoServiceInterface):
    def __init__(self, fal_client: FalClient = Depends()):
        self.fal_client = fal_client

    async def generate_video(self, request: GenerateVideoRequest) -> Dict[str, Any]:
        content = request.content or {}

        if request.type == VideoType.animated_scene:
            return await self.fal_client.kling_image_to_video(
                prompt=content.get("prompt"),
                image_url=content.get("image_url"),
                fal_webhook=content.get("fal_webhook")
            )

        if request.type == VideoType.human_scene:
            return await self.fal_client.bytedance_omnihuman(
                image_url=content.get("image_url"),
                audio_url=content.get("audio_url"),
                fal_webhook=content.get("fal_webhook")
            )
```

---

## AudioService

Servicio para generación de audio (Text-to-Speech).

```python
class AudioService(AudioServiceInterface):
    def __init__(self, fal_client: FalClient = Depends()):
        self.fal_client = fal_client

    async def generate_audio(self, request: GenerateAudioRequest) -> Dict[str, Any]:
        if not request.text:
            raise HTTPException(status_code=400, detail="Falta 'text'")

        content = request.content or {}
        fal_webhook = content.get("fal_webhook")

        return await self.fal_client.tts_multilingual_v2(
            text=request.text,
            fal_webhook=fal_webhook,
            **{k: v for k, v in content.items() if k != "fal_webhook"}
        )
```

---

## DropiService

Servicio para integración con la plataforma Dropi.

```python
class DropiService(DropiServiceInterface):
    async def get_departments(self, country: str = "co") -> List[Dict[str, Any]]:
        response = await dropi_client.get_departments(country)
        return response.get("objects", [])

    async def get_cities_by_department(self, department_id: int, 
                                        country: str = "co") -> List[Dict[str, Any]]:
        rate_type = "CON RECAUDO"
        response = await dropi_client.get_cities_by_department(
            department_id, rate_type, country
        )
        return response.get("objects", {}).get("cities", [])
```

---

## ProductScrapingService

Servicio para scraping de productos (ver [Scrapers](./scrapers.md)).

```python
class ProductScrapingService(ProductScrapingServiceInterface):
    def __init__(self, scraping_factory: ScrapingFactory = Depends()):
        self.scraping_factory = scraping_factory

    async def scrape_product(self, request: ProductScrapingRequest):
        url = str(request.product_url)
        domain = urlparse(url).netloc.lower()

        scraper = self.scraping_factory.get_scraper(url, country=request.country)
        return await scraper.scrape(url, domain)
```

---

## Interfaces de Servicio

Cada servicio tiene una interfaz que permite la inyección de dependencias:

```python
# message_service_interface.py
class MessageServiceInterface(ABC):
    @abstractmethod
    async def handle_message(self, request: MessageRequest) -> dict:
        pass

# image_service_interface.py
class ImageServiceInterface(ABC):
    @abstractmethod
    async def generate_variation_images(self, request, owner_id) -> GenerateImageResponse:
        pass

# Inyección en main.py
app.dependency_overrides[MessageServiceInterface] = MessageService
app.dependency_overrides[ImageServiceInterface] = ImageService
```

## Procesamiento Paralelo

Los servicios utilizan `asyncio.gather` para procesar múltiples tareas en paralelo:

```python
async def process_multiple_agents(self, agent_queries: list[dict]) -> dict:
    tasks = [
        self.handle_message(MessageRequest(
            agent_id=item['agent'],
            query=item['query']
        )) for item in agent_queries
    ]

    responses = await asyncio.gather(*tasks, return_exceptions=True)

    combined_data = {}
    for response in responses:
        if not isinstance(response, Exception):
            data = json.loads(response['text'])
            combined_data.update(data)

    return combined_data
```

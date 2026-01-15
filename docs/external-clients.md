# Clientes Externos

El sistema se integra con múltiples servicios externos para funcionalidades específicas.

## Agent Config Client

Cliente para obtener la configuración de agentes desde el servicio externo.

### Endpoint

```
POST {HOST_AGENT_CONFIG}/api/ms/agent/config/search-agent
```

### Implementación

```python
async def get_agent(data: AgentConfigRequest) -> AgentConfigResponse:
    endpoint = '/api/ms/agent/config/search-agent'
    url = f"{HOST_AGENT_CONFIG}{endpoint}"
    headers = {'Content-Type': 'application/json'}

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data.model_dump(), headers=headers)
        response.raise_for_status()
        return AgentConfigResponse(**response.json())
```

### Estructura de Respuesta

```python
class AgentConfigResponse(BaseModel):
    id: int
    agent_id: str
    description: str
    prompt: str
    provider_ai: str  # openai, claude, gemini, deepseek
    model_ai: str     # gpt-4, claude-3-sonnet, etc.
    preferences: AgentPreferences
    tools: Optional[List[Dict[str, Any]]]
    mcp_config: Optional[Dict[str, Any]]

class AgentPreferences(BaseModel):
    temperature: float = 0.7
    max_tokens: int = 1000
    top_p: float = 1.0
    extra_parameters: Optional[Dict[str, Any]] = None
```

---

## FAL Client

Cliente para el servicio FAL AI (generación de video y audio).

### Configuración

```python
class FalClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or FAL_AI_API_KEY
```

### Métodos

#### Text-to-Speech Multilingüe

```python
async def tts_multilingual_v2(self, text: str, fal_webhook: Optional[str] = None, **kwargs):
    payload = {"text": text}
    payload.update(kwargs)
    return await self._post("fal-ai/elevenlabs/tts/multilingual-v2", payload, fal_webhook)
```

#### Video desde Imagen (Kling)

```python
async def kling_image_to_video(self, prompt: str, image_url: str, 
                                fal_webhook: Optional[str] = None, **kwargs):
    payload = {"prompt": prompt, "image_url": image_url}
    payload.update(kwargs)
    return await self._post("fal-ai/kling-video/v2/master/image-to-video", payload, fal_webhook)
```

#### Video con Humano (OmniHuman)

```python
async def bytedance_omnihuman(self, image_url: str, audio_url: str, 
                               fal_webhook: Optional[str] = None, **kwargs):
    payload = {"image_url": image_url, "audio_url": audio_url}
    payload.update(kwargs)
    return await self._post("fal-ai/bytedance/omnihuman", payload, fal_webhook)
```

### Soporte para Webhooks

FAL soporta webhooks para notificaciones asíncronas:

```python
async def _post(self, path: str, payload: Dict, fal_webhook: Optional[str] = None):
    base_url = f"https://queue.fal.run/{path}"
    if fal_webhook:
        query = f"fal_webhook={urllib.parse.quote_plus(fal_webhook)}"
        url = f"{base_url}?{query}"
    else:
        url = base_url
    
    headers = {
        "Authorization": f"Key {self.api_key}",
        "Content-Type": "application/json",
    }
    
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(url, json=payload, headers=headers)
        return response.json()
```

---

## Google Vision Client

Cliente para el servicio Google Cloud Vision.

### Funcionalidad

- Detección de etiquetas (LABEL_DETECTION)
- Detección de logos (LOGO_DETECTION)

### Implementación

```python
async def analyze_image(image_base64: str) -> VisionAnalysisResponse:
    vision_api_url = f"https://vision.googleapis.com/v1/images:annotate?key={GOOGLE_VISION_API_KEY}"

    payload = {
        "requests": [{
            "image": {"content": image_base64},
            "features": [
                {"type": "LABEL_DETECTION", "maxResults": 3},
                {"type": "LOGO_DETECTION", "maxResults": 1}
            ]
        }]
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(vision_api_url, json=payload) as response:
            data = await response.json()
            
            # Extraer logo (si score > 0.65)
            logo_description = ""
            if data["responses"][0].get("logoAnnotations"):
                logo = data["responses"][0]["logoAnnotations"][0]
                if logo.get("score", 0) > 0.65:
                    logo_description = logo["description"]

            # Extraer etiquetas (si score > 0.65)
            labels = [
                label["description"]
                for label in data["responses"][0].get("labelAnnotations", [])
                if label.get("score", 0) > 0.65
            ]

            return VisionAnalysisResponse(
                logo_description=logo_description,
                label_description=", ".join(labels)
            )
```

### Respuesta

```python
class VisionAnalysisResponse(BaseModel):
    logo_description: str
    label_description: str

    def get_analysis_text(self) -> str:
        parts = []
        if self.logo_description:
            parts.append(f"Logo detected: {self.logo_description}")
        if self.label_description:
            parts.append(f"Labels: {self.label_description}")
        return ". ".join(parts)
```

---

## Dropi Client

Cliente para la plataforma Dropi (dropshipping).

### Configuración Multi-País

```python
DROPI_HOST = os.getenv('DROPI_HOST', 'https://test-api.dropi.co')

def get_dropi_api_key(country: str = "co") -> str:
    country_keys = {
        "co": DROPI_API_KEY_CO,
        "mx": DROPI_API_KEY_MX,
        "ar": DROPI_API_KEY_AR,
        "cl": DROPI_API_KEY_CL,
        "pe": DROPI_API_KEY_PE,
        "py": DROPI_API_KEY_PY,
        "ec": DROPI_API_KEY_EC,
    }
    return country_keys.get(country.lower(), DROPI_API_KEY)
```

### Métodos

#### Obtener Detalles de Producto

```python
async def get_product_details(product_id: str, country: str = "co") -> Dict[str, Any]:
    headers = {"dropi-integration-key": get_dropi_api_key(country)}
    dropi_host = DROPI_HOST.replace(".co", f".{country}")
    url = f"{dropi_host}/integrations/products/v2/{product_id}"

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        return response.json()
```

#### Obtener Departamentos

```python
async def get_departments(country: str = "co") -> Dict[str, Any]:
    headers = {"dropi-integration-key": get_dropi_api_key(country)}
    dropi_host = DROPI_HOST.replace(".co", f".{country}")
    url = f"{dropi_host}/integrations/department"

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        return response.json()
```

#### Obtener Ciudades por Departamento

```python
async def get_cities_by_department(department_id: int, rate_type: str, 
                                    country: str = "co") -> Dict[str, Any]:
    headers = {
        "dropi-integration-key": get_dropi_api_key(country),
        "Content-Type": "application/json"
    }
    payload = {"department_id": department_id, "rate_type": rate_type}
    
    dropi_host = DROPI_HOST.replace(".co", f".{country}")
    url = f"{dropi_host}/integrations/trajectory/bycity"

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)
        return response.json()
```

---

## Amazon Client

Cliente para la API de Amazon via RapidAPI.

### Endpoints

- Búsqueda de productos
- Detalles de producto por ASIN

### Implementación

```python
async def search_products(request: AmazonSearchRequest):
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://{RAPIDAPI_HOST}/search",
            params={"query": request.query},
            headers=headers
        )
        return response.json()

async def get_product_details(asin: str):
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://{RAPIDAPI_HOST}/product-details",
            params={"asin": asin},
            headers=headers
        )
        return response.json()
```

---

## AliExpress Client

Cliente para la API de AliExpress via RapidAPI.

### Obtener Detalles de Producto

```python
async def get_item_detail(item_id: str) -> Dict[str, Any]:
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "aliexpress-datahub.p.rapidapi.com"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://aliexpress-datahub.p.rapidapi.com/item_detail_2",
            params={"itemId": item_id},
            headers=headers
        )
        return response.json()
```

---

## S3 Upload Client

Cliente para subir archivos a S3.

### Subir Archivo

```python
async def upload_file(request: S3UploadRequest) -> S3UploadResponse:
    url = f"{S3_UPLOAD_API}/upload"
    
    payload = {
        "file": request.file,  # Base64
        "folder": request.folder,
        "filename": request.filename
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)
        return S3UploadResponse(**response.json())
```

### Verificar si Existe

```python
async def check_file_exists_direct(s3_url: str) -> bool:
    async with httpx.AsyncClient() as client:
        response = await client.head(s3_url)
        return response.status_code == 200
```

---

## ScraperAPI Client

Cliente para el servicio ScraperAPI.

### Obtener HTML de una URL

```python
class ScraperAPIClient:
    async def get_html(self, url: str) -> str:
        params = {
            "api_key": SCRAPERAPI_KEY,
            "url": url,
            "render": "true"
        }
        
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(
                "https://api.scraperapi.com",
                params=params
            )
            return response.text

    async def get_html_lambda(self, url: str) -> str:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                URL_SCRAPER_LAMBDA,
                json={"url": url}
            )
            return response.json().get("html", "")
```

---

## Resumen de Variables de Entorno

| Cliente | Variables Requeridas |
|---------|---------------------|
| Agent Config | `HOST_AGENT_CONFIG` |
| FAL | `FAL_AI_API_KEY` |
| Google Vision | `GOOGLE_VISION_API_KEY` |
| Dropi | `DROPI_HOST`, `DROPI_API_KEY`, `DROPI_API_KEY_*` |
| Amazon | `RAPIDAPI_KEY`, `RAPIDAPI_HOST` |
| AliExpress | `RAPIDAPI_KEY` |
| S3 | `S3_UPLOAD_API` |
| ScraperAPI | `SCRAPERAPI_KEY`, `URL_SCRAPER_LAMBDA` |

# API Endpoints

Todos los endpoints están prefijados con `/api/ms/conversational-engine`.

## Índice de Endpoints

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| POST | `/handle-message` | Procesar mensaje conversacional | No |
| POST | `/handle-message-json` | Procesar mensaje con respuesta JSON | No |
| POST | `/recommend-product` | Recomendar productos | No |
| POST | `/generate-pdf` | Generar PDF manual | No |
| POST | `/generate-variation-images` | Generar variaciones de imagen | Bearer |
| POST | `/generate-images-from` | Generar imágenes desde prompt | Bearer |
| POST | `/generate-images-from/api-key` | Generar imágenes (API Key) | API Key |
| POST | `/generate-images-from-agent/api-key` | Generar imágenes con agente | API Key |
| POST | `/generate-copies` | Generar copys de marketing | No |
| POST | `/scrape-product` | Scraping de producto | Bearer |
| POST | `/scrape-direct-html` | Scraping directo de HTML | Bearer |
| POST | `/resolve-info-funnel` | Resolver información de funnel | No |
| POST | `/store/brand-context-resolver` | Resolver contexto de marca | Bearer |
| POST | `/generate-video` | Generar video con IA | No |
| POST | `/generate-audio` | Generar audio (TTS) | No |
| GET | `/integration/dropi/departments` | Obtener departamentos Dropi | No |
| GET | `/integration/dropi/departments/{id}/cities` | Obtener ciudades por departamento | No |
| GET | `/health` | Health check | No |

---

## Mensajería y Conversación

### POST /handle-message

Procesa un mensaje y retorna la respuesta del agente de IA.

**Request Body:**

```json
{
  "agent_id": "string",
  "conversation_id": "string",
  "query": "string",
  "metadata_filter": [
    {
      "key": "string",
      "value": "string",
      "evaluator": "="
    }
  ],
  "parameter_prompt": {
    "key": "value"
  },
  "files": [
    {
      "type": "image",
      "url": "https://example.com/image.jpg",
      "content": "base64_string"
    }
  ],
  "json_parser": {
    "field": "type"
  }
}
```

**Campos:**

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| agent_id | string | Sí | ID del agente a utilizar |
| conversation_id | string | Sí | ID de la conversación (vacío para nueva) |
| query | string | Sí | Mensaje del usuario |
| metadata_filter | array | No | Filtros de metadatos |
| parameter_prompt | object | No | Parámetros adicionales para el prompt |
| files | array | No | Archivos adjuntos |
| json_parser | object | No | Esquema esperado de respuesta JSON |

**Response:**

```json
{
  "context": "string",
  "chat_history": [],
  "input": "string",
  "text": "Respuesta del agente"
}
```

---

### POST /handle-message-json

Similar a `/handle-message` pero parsea la respuesta como JSON.

**Response:**

Retorna directamente el JSON parseado de la respuesta del agente.

---

## Recomendación de Productos

### POST /recommend-product

Recomienda productos basándose en nombre y descripción.

**Request Body:**

```json
{
  "product_name": "string",
  "product_description": "string",
  "similar": false
}
```

**Response:**

```json
{
  "ai_response": {
    "recommended_product": "string"
  },
  "products": [
    {
      "asin": "string",
      "title": "string",
      "price": "string",
      "image": "string"
    }
  ]
}
```

---

## Generación de Contenido

### POST /generate-pdf

Genera un manual PDF para un producto.

**Request Body:**

```json
{
  "product_id": "string",
  "product_name": "string",
  "product_description": "string",
  "language": "es",
  "content": "string",
  "title": "string",
  "image_url": "string",
  "owner_id": "string"
}
```

**Response:**

```json
{
  "s3_url": "https://fluxi.co/..."
}
```

---

### POST /generate-copies

Genera textos de marketing (copys).

**Request Body:**

```json
{
  "prompt": "string"
}
```

**Response:**

```json
{
  "copies": {
    "headline": "string",
    "subheadline": "string",
    "cta": "string"
  }
}
```

---

## Generación de Imágenes

### POST /generate-variation-images

Genera variaciones de una imagen existente.

**Headers:**
- `Authorization: Bearer <token>`

**Request Body:**

```json
{
  "file": "base64_encoded_image",
  "num_variations": 3,
  "language": "es"
}
```

**Response:**

```json
{
  "generated_urls": ["url1", "url2", "url3"],
  "original_url": "string",
  "original_urls": ["string"],
  "generated_prompt": "string",
  "vision_analysis": {
    "logo_description": "string",
    "label_description": "string"
  }
}
```

---

### POST /generate-images-from

Genera imágenes desde un prompt y/o imagen base.

**Headers:**
- `Authorization: Bearer <token>`

**Request Body:**

```json
{
  "file": "base64_encoded_image",
  "file_url": "https://example.com/image.jpg",
  "file_urls": ["url1", "url2"],
  "prompt": "string",
  "num_variations": 1,
  "provider": "openai",
  "model_ai": "dall-e-3",
  "extra_parameters": {},
  "language": "es"
}
```

---

## Generación de Video

### POST /generate-video

Genera videos usando FAL AI.

**Request Body:**

```json
{
  "type": "animated_scene",
  "content": {
    "prompt": "string",
    "image_url": "string",
    "fal_webhook": "string"
  }
}
```

**Tipos de video:**

| Tipo | Descripción | Campos requeridos |
|------|-------------|-------------------|
| `animated_scene` | Escena animada | prompt, image_url |
| `human_scene` | Escena con humano | image_url, audio_url |

---

## Generación de Audio

### POST /generate-audio

Genera audio usando Text-to-Speech.

**Request Body:**

```json
{
  "text": "Texto a convertir en audio",
  "content": {
    "fal_webhook": "string",
    "voice_id": "string"
  }
}
```

---

## Scraping de Productos

### POST /scrape-product

Extrae información de un producto desde su URL.

**Headers:**
- `Authorization: Bearer <token>`

**Request Body:**

```json
{
  "product_url": "https://www.amazon.com/dp/B01234567",
  "country": "co"
}
```

**Response:**

```json
{
  "data": {
    "provider_id": "amazon",
    "external_id": "B01234567",
    "name": "Nombre del producto",
    "description": "Descripción",
    "external_sell_price": 29.99,
    "images": ["url1", "url2"],
    "variants": []
  }
}
```

---

## Funnel y Marca

### POST /resolve-info-funnel

Analiza un producto para generar información de funnel de ventas.

**Request Body:**

```json
{
  "product_name": "string",
  "product_description": "string",
  "language": "es"
}
```

**Response:**

```json
{
  "pain_detection": "string",
  "buyer_detection": "string",
  "sales_angles": [
    {
      "name": "string",
      "description": "string"
    }
  ]
}
```

---

### POST /store/brand-context-resolver

Resuelve el contexto de marca para una tienda.

**Headers:**
- `Authorization: Bearer <token>`

**Request Body:**

```json
{
  "prompt": {
    "store_info": "string"
  }
}
```

**Response:**

```json
{
  "brands": ["brand1", "brand2"],
  "contexts": ["context1", "context2"]
}
```

---

## Integración Dropi

### GET /integration/dropi/departments

Obtiene la lista de departamentos.

**Query Parameters:**
- `country`: Código de país (default: "co")

---

### GET /integration/dropi/departments/{department_id}/cities

Obtiene las ciudades de un departamento.

**Path Parameters:**
- `department_id`: ID del departamento

**Query Parameters:**
- `country`: Código de país (default: "co")

---

## Health Check

### GET /health

Verifica el estado del servicio.

**Response:**

```json
{
  "status": "OK"
}
```

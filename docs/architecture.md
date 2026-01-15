# Arquitectura del Sistema

## Diagrama de Arquitectura

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Cliente (HTTP Request)                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FastAPI Application                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                         Middlewares (Auth)                               ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                          Controllers/Router                              ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
          ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
          │ MessageService  │ │  ImageService   │ │ProductScraping  │
          │                 │ │                 │ │    Service      │
          └────────┬────────┘ └────────┬────────┘ └────────┬────────┘
                   │                   │                   │
                   ▼                   ▼                   ▼
          ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
          │ Conversation    │ │ External APIs   │ │ ScrapingFactory │
          │   Manager       │ │ (Google Vision, │ │                 │
          │                 │ │  S3, FAL)       │ │                 │
          └────────┬────────┘ └─────────────────┘ └────────┬────────┘
                   │                                       │
                   ▼                                       ▼
          ┌─────────────────┐                     ┌─────────────────┐
          │   Processors    │                     │    Scrapers     │
          │ ┌─────────────┐ │                     │ ┌─────────────┐ │
          │ │   Simple    │ │                     │ │   Amazon    │ │
          │ │  Processor  │ │                     │ │   Scraper   │ │
          │ └─────────────┘ │                     │ └─────────────┘ │
          │ ┌─────────────┐ │                     │ ┌─────────────┐ │
          │ │   Agent     │ │                     │ │ AliExpress  │ │
          │ │  Processor  │ │                     │ │   Scraper   │ │
          │ └─────────────┘ │                     │ └─────────────┘ │
          │ ┌─────────────┐ │                     │ ┌─────────────┐ │
          │ │    MCP      │ │                     │ │   Dropi     │ │
          │ │  Processor  │ │                     │ │   Scraper   │ │
          │ └─────────────┘ │                     │ └─────────────┘ │
          └────────┬────────┘                     │ ┌─────────────┐ │
                   │                              │ │  IA Scraper │ │
                   ▼                              │ └─────────────┘ │
          ┌─────────────────┐                     └─────────────────┘
          │ AI Provider     │
          │    Factory      │
          │ ┌─────────────┐ │
          │ │   OpenAI    │ │
          │ └─────────────┘ │
          │ ┌─────────────┐ │
          │ │  Anthropic  │ │
          │ └─────────────┘ │
          │ ┌─────────────┐ │
          │ │   Gemini    │ │
          │ └─────────────┘ │
          │ ┌─────────────┐ │
          │ │  DeepSeek   │ │
          │ └─────────────┘ │
          └─────────────────┘
```

## Componentes Principales

### 1. Capa de Entrada (Controllers)

**handle_controller.py**
- Punto de entrada para todas las solicitudes HTTP
- Define los endpoints de la API
- Inyecta dependencias de servicios
- Aplica middlewares de autenticación

### 2. Capa de Servicios

| Servicio | Descripción |
|----------|-------------|
| `MessageService` | Procesamiento principal de mensajes y conversaciones |
| `ImageService` | Generación y variación de imágenes |
| `VideoService` | Generación de videos con FAL AI |
| `AudioService` | Generación de audio (TTS) |
| `ProductScrapingService` | Scraping de productos de e-commerce |
| `DropiService` | Integración con la plataforma Dropi |

### 3. Gestión de Conversaciones

**ConversationManager**
- Almacena el historial de conversaciones en memoria
- Límite configurable de historial (10 mensajes por defecto)
- Selecciona el procesador adecuado según la configuración del agente

### 4. Procesadores

| Procesador | Uso |
|------------|-----|
| `SimpleProcessor` | Conversaciones simples sin herramientas |
| `AgentProcessor` | Agentes con herramientas dinámicas |
| `MCPProcessor` | Agentes con Model Context Protocol |

### 5. Proveedores de IA

Implementación del patrón Factory para manejar múltiples proveedores:

- **OpenAI**: GPT-4, GPT-3.5, etc.
- **Anthropic**: Claude 3 (Opus, Sonnet, Haiku)
- **Gemini**: Google Gemini Pro
- **DeepSeek**: Modelos DeepSeek via Ollama

### 6. Sistema de Scraping

Factory pattern para seleccionar el scraper correcto:

- **AmazonScraper**: Productos de Amazon
- **AliexpressScraper**: Productos de AliExpress
- **DropiScraper**: Productos de Dropi
- **CJScraper**: Productos de CJ Dropshipping
- **IAScraper**: Scraping genérico con IA

## Flujo de Datos

### Procesamiento de Mensaje

```
1. Request HTTP → Controller
2. Controller → MessageService
3. MessageService → AgentConfigClient (obtener configuración)
4. MessageService → ConversationManager
5. ConversationManager → AIProviderFactory (crear LLM)
6. ConversationManager → Processor (según configuración)
7. Processor → LLM (procesar query)
8. Response → Cliente
```

### Scraping de Producto

```
1. Request HTTP → Controller
2. Controller → ProductScrapingService
3. ProductScrapingService → ScrapingFactory
4. ScrapingFactory → Scraper específico (según URL)
5. Scraper → API externa o HTML parsing
6. Response estructurada → Cliente
```

## Patrones de Diseño

1. **Factory Pattern**: AIProviderFactory, ScrapingFactory
2. **Strategy Pattern**: Procesadores intercambiables
3. **Dependency Injection**: FastAPI Depends
4. **Interface Segregation**: Interfaces para cada servicio
5. **Repository Pattern**: ConversationManager para historial

## Escalabilidad

- **Stateless**: Cada request es independiente (excepto historial en memoria)
- **Async/Await**: Operaciones I/O no bloqueantes
- **Docker Ready**: Containerización lista
- **Horizontal Scaling**: Puede ejecutarse en múltiples instancias (considerar Redis para historial compartido)

# Documentación del Conversational Engine

## Descripción General

**Conversational Engine** es un microservicio construido con Python y FastAPI que actúa como motor de conversación con inteligencia artificial. Se integra con múltiples proveedores de IA (OpenAI, Anthropic Claude, Google Gemini, DeepSeek) y servicios externos para procesar consultas de usuarios, generar contenido, realizar scraping de productos y mucho más.

## Índice de Documentación

1. [Arquitectura](./architecture.md) - Visión general de la arquitectura del sistema
2. [Instalación y Configuración](./installation.md) - Guía de instalación y configuración
3. [API Endpoints](./api-endpoints.md) - Documentación de todos los endpoints
4. [Proveedores de IA](./ai-providers.md) - Integración con proveedores de IA
5. [Procesadores](./processors.md) - Sistema de procesamiento de conversaciones
6. [Scrapers](./scrapers.md) - Sistema de scraping de productos
7. [Servicios](./services.md) - Documentación de servicios internos
8. [Clientes Externos](./external-clients.md) - Integraciones con servicios externos
9. [Middlewares](./middlewares.md) - Autenticación y seguridad
10. [Variables de Entorno](./environment-variables.md) - Configuración del entorno

## Características Principales

- **Procesamiento de Conversaciones**: Manejo inteligente de conversaciones con historial y contexto
- **Multi-Proveedor de IA**: Soporte para OpenAI, Claude, Gemini y DeepSeek
- **Generación de Imágenes**: Creación y variación de imágenes con IA
- **Generación de Video**: Creación de videos animados y escenas humanas
- **Generación de Audio**: Text-to-speech multilingüe
- **Scraping de Productos**: Extracción de datos de Amazon, AliExpress, Dropi y más
- **Generación de PDFs**: Creación de manuales y documentos
- **Integración MCP**: Soporte para Model Context Protocol
- **Tools Dinámicas**: Generación dinámica de herramientas para agentes

## Tecnologías Utilizadas

- **Python 3.10+**
- **FastAPI** - Framework web asíncrono
- **LangChain** - Orquestación de LLMs
- **LangGraph** - Grafos de agentes
- **Pydantic** - Validación de datos
- **httpx** - Cliente HTTP asíncrono
- **FPDF** - Generación de PDFs

## Inicio Rápido

```bash
# Clonar el repositorio
git clone <repository-url>

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env

# Ejecutar el servidor
python main.py
```

El servidor estará disponible en `http://localhost:8000`

## Documentación Swagger

Una vez que el servidor esté corriendo, accede a la documentación interactiva en:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

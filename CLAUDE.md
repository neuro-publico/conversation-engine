# Conversation Engine

Microservicio de agentes conversacionales multi-proveedor de IA para la plataforma Fluxi. Procesa mensajes, genera imágenes/video/audio, y hace scraping de productos e-commerce.

## Tech Stack

- **Python 3.10** con **FastAPI** (async-first)
- **LangChain + LangGraph** para orquestación de LLMs
- **Proveedores de IA**: OpenAI, Anthropic, Gemini, DeepSeek (via Factory pattern)
- **httpx** para HTTP async, **requests** para sync
- **Pydantic 2** para validación de datos
- **pytest + pytest-asyncio** para testing
- **black + isort + flake8** para code quality

## Commands

```bash
make run              # uvicorn en puerto 8000 con reload
make install          # pip install -r requirements.txt
make test             # pytest completo
make test-unit        # Solo unit tests
make test-integration # Solo integration tests
make test-cov         # Tests con coverage (HTML en htmlcov/)
make format           # Auto-format con black + isort
make lint             # Verificar con black, isort, flake8
make clean            # Limpiar cache y .pyc
```

## Project Structure

```
app/
├── controllers/       # Endpoints FastAPI (handle_controller.py)
├── services/          # Lógica de negocio (message, image, video, audio, scraping)
├── processors/        # Procesadores LLM (simple, agent, mcp)
├── providers/         # Implementaciones de AI providers (openai, anthropic, gemini, deepseek)
├── factories/         # Factory pattern (ai_provider, scraping)
├── scrapers/          # Scrapers de e-commerce (amazon, aliexpress, dropi, cj, ia)
├── externals/         # Clientes de APIs externas (agent_config, s3, fal, google_vision)
├── managers/          # Estado en memoria (conversation history)
├── middlewares/       # Auth middleware (API key + JWT)
├── requests/          # DTOs de request (Pydantic models)
├── responses/         # DTOs de response
├── tools/             # Generación dinámica de tools para LangChain
├── pdf/               # Generación de PDFs
├── helpers/           # Utilidades (escape, image compression)
├── configurations/    # Config y constantes
└── requestors/        # HTTP request executors para tools
tests/
├── conftest.py        # Fixtures compartidos
├── unit/              # Tests unitarios por módulo
└── integration/       # Tests de integración
```

## Conventions

- Archivos: `{dominio}_service.py`, `{plataforma}_scraper.py`, `{provider}_provider.py`
- Clases: **PascalCase** — `MessageService`, `AmazonScraper`
- Interfaces: sufijo `Interface` — `ServiceInterface`, `ScraperInterface`
- Tests: `test_{modulo}.py` con clases `Test{Componente}`
- Funciones async: `async def handle_message()`, privadas con `_prefijo()`
- Tests marcados con `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`
- Line length: **120 caracteres** (black/flake8)
- Type hints explícitos en todas las funciones
- Pydantic models para todo request/response

## Design Patterns

- **Factory**: `AIProviderFactory` y `ScrapingFactory` para seleccionar implementaciones
- **Strategy**: `ConversationProcessor` → `SimpleProcessor`, `AgentProcessor`, `MCPProcessor`
- **Interface Segregation**: toda service/scraper/provider tiene su `*Interface`
- **Dependency Injection**: FastAPI `Depends()` en todo el proyecto
- **Tool Generation**: tools dinámicos desde config → Pydantic model → LangChain `StructuredTool`

## Authentication

- `@require_api_key`: header `x-api-key`, compara contra env `API_KEY`
- `@require_auth`: header `authorization` Bearer, valida JWT contra `AUTH_SERVICE_URL`
- User info disponible en `request.state.user_info` post-auth

## Key Environment Variables

```
HOST_AGENT_CONFIG          # URL del servicio de config de agentes
OPENAI_API_KEY             # API key de OpenAI
ANTHROPIC_API_KEY          # API key de Anthropic
GOOGLE_GEMINI_API_KEY      # API key de Gemini
API_KEY                    # API key para auth de endpoints
AUTH_SERVICE_URL           # URL del servicio de auth (JWT)
S3_UPLOAD_API              # URL del servicio de upload a S3
ENVIRONMENT                # dev | prod
FAL_AI_API_KEY             # FAL AI para video/audio
DROPI_API_KEY              # Dropi (+ sufijos por país: _CO, _MX, _AR, etc.)
LANGCHAIN_API_KEY          # LangSmith monitoring
```

## Testing

- Coverage mínimo: **60%** (enforced en CI)
- Fixtures extensos en `conftest.py` (mocks de httpx, LLM, services)
- CI: GitHub Actions → lint → test → coverage → Codecov

## Git Rules

- Nunca hacer commits directos a `main`, `master` o `develop` — siempre crear una rama y abrir un PR
- Siempre correr los tests antes de hacer commit. Si los tests no pasan, no hacer el commit
- **`develop` SIEMPRE debe estar deployable** — solo mergear features completos y probados en local. NUNCA dejar trabajo incompleto en develop.
- **Probar en local primero** — levantar servicios locales, hacer pruebas end-to-end en localhost. Solo mergear cuando el feature funciona completo.
- **1 PR completo por feature** — no PRs incrementales que dejan el feature a medio hacer en dev.
- **Si algo se mergeó y falló**: arreglar inmediatamente o revertir. Dev siempre limpio.

## Rules

- Siempre correr `make format` antes de commitear
- Toda función nueva debe tener type hints completos
- Todo service/provider/scraper nuevo debe implementar su interface correspondiente
- No agregar estado persistente — el servicio es stateless (conversation history es in-memory)
- Para nuevo AI provider: crear en `providers/`, registrar en `AIProviderFactory`
- Para nuevo scraper: crear en `scrapers/`, registrar en `ScrapingFactory`
- No modificar el Dockerfile sin coordinar con DevOps
- Mantener coverage ≥ 60% — todo código nuevo debe tener tests

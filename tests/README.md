# Tests para Conversational Engine

Este directorio contiene los tests unitarios e integración para el proyecto conversational-engine.

## Estructura

```
tests/
├── conftest.py              # Fixtures globales compartidas
├── unit/                    # Tests unitarios
│   ├── factories/           # Tests para AIProviderFactory, ScrapingFactory
│   ├── providers/           # Tests para proveedores de IA
│   ├── scrapers/            # Tests para scrapers de productos
│   ├── helpers/             # Tests para helpers (escape, compression)
│   ├── services/            # Tests para servicios principales
│   ├── processors/          # Tests para procesadores de conversación
│   ├── managers/            # Tests para ConversationManager
│   ├── middlewares/         # Tests para middlewares de auth
│   ├── externals/           # Tests para clientes externos (FAL, Vision)
│   ├── models/              # Tests para modelos Pydantic
│   └── tools/               # Tests para ToolGenerator
└── integration/             # Tests de integración
    └── test_api_endpoints.py  # Tests de endpoints de la API
```

## Comandos Rápidos (Makefile)

```bash
# Ejecutar todos los tests
make test

# Tests con cobertura
make test-cov

# Solo tests unitarios
make test-unit

# Solo tests de integración
make test-integration

# Verificar formato y linting
make lint

# Formatear código automáticamente
make format
```

## Ejecutar Tests Manualmente

### Todos los tests

```bash
pytest
```

### Solo tests unitarios

```bash
pytest tests/unit -v
```

### Solo tests de integración

```bash
pytest tests/integration -v
```

### Tests con cobertura

```bash
pytest --cov=app --cov-report=html
```

### Tests específicos por módulo

```bash
# Factories
pytest tests/unit/factories -v

# Providers
pytest tests/unit/providers -v

# Scrapers
pytest tests/unit/scrapers -v

# Services
pytest tests/unit/services -v

# Processors
pytest tests/unit/processors -v
```

### Tests por marcador

```bash
# Solo tests unitarios
pytest -m unit

# Solo tests de integración
pytest -m integration

# Tests lentos
pytest -m slow
```

## Fixtures Disponibles

Las fixtures globales están definidas en `conftest.py`:

### Datos de Ejemplo
- `sample_message_request_data`: Datos para MessageRequest
- `sample_agent_config_data`: Datos para AgentConfigResponse
- `sample_product_data`: Datos de producto scrapeado
- `sample_amazon_product_data`: Respuesta de Amazon
- `sample_aliexpress_product_data`: Respuesta de AliExpress

### Mocks de Servicios
- `mock_httpx_client`: Mock para httpx.AsyncClient
- `mock_llm`: Mock para modelos de lenguaje
- `mock_agent_config`: Mock de AgentConfigResponse
- `mock_conversation_manager`: Mock de ConversationManager
- `mock_message_service`: Mock de MessageService
- `mock_fal_client`: Mock de FalClient

### Otros
- `mock_request`: Mock de FastAPI Request
- `sample_base64_image`: Imagen de prueba en base64
- `sample_html_content`: HTML de ejemplo
- `sample_tool_config`: Configuración de herramienta
- `mock_env_vars`: Variables de entorno mockeadas

## Escribir Nuevos Tests

### Convenciones

1. **Nombres de archivos**: `test_<modulo>.py`
2. **Nombres de clases**: `Test<Componente>`
3. **Nombres de funciones**: `test_<accion>_<resultado_esperado>`

### Ejemplo

```python
import pytest
from app.module import MyClass

class TestMyClass:
    """Tests para MyClass."""
    
    @pytest.fixture
    def instance(self):
        """Crear instancia de prueba."""
        return MyClass()
    
    @pytest.mark.unit
    def test_method_returns_expected(self, instance):
        """El método debe retornar el valor esperado."""
        result = instance.method()
        assert result == expected_value
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_async_method(self, instance):
        """El método async debe funcionar correctamente."""
        result = await instance.async_method()
        assert result is not None
```

### Marcadores Disponibles

- `@pytest.mark.unit`: Tests unitarios
- `@pytest.mark.integration`: Tests de integración
- `@pytest.mark.slow`: Tests que tardan mucho
- `@pytest.mark.asyncio`: Tests asíncronos

## CI/CD

Para ejecutar en CI:

```bash
# Instalar dependencias de test
pip install pytest pytest-asyncio pytest-cov

# Ejecutar tests con reporte de cobertura
pytest --cov=app --cov-report=xml --junitxml=test-results.xml
```

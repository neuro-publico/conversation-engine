# Proveedores de IA

El sistema soporta múltiples proveedores de IA a través de un patrón Factory que permite intercambiarlos fácilmente.

## Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                     AIProviderFactory                        │
│  ┌─────────────────────────────────────────────────────────┐│
│  │              get_provider(provider_name)                 ││
│  └─────────────────────────────────────────────────────────┘│
└──────────────────────────┬──────────────────────────────────┘
                           │
       ┌───────────────────┼───────────────────┐
       ▼                   ▼                   ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   OpenAI    │     │  Anthropic  │     │   Gemini    │
│  Provider   │     │   Provider  │     │  Provider   │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       ▼                   ▼                   ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  ChatOpenAI │     │ChatAnthropic│     │ ChatGoogle  │
│             │     │             │     │ GenerativeAI│
└─────────────┘     └─────────────┘     └─────────────┘
```

## AIProviderInterface

Interfaz base que todos los proveedores deben implementar:

```python
class AIProviderInterface(ABC):
    @abstractmethod
    def get_llm(self, model: str, temperature: float, 
                max_tokens: int, top_p: float) -> BaseChatModel:
        """Retorna el modelo de lenguaje configurado"""
        pass

    @abstractmethod
    def supports_interleaved_files(self) -> bool:
        """Indica si soporta archivos intercalados en el contexto"""
        pass
```

## Proveedores Disponibles

### 1. OpenAI Provider

**Identificador:** `openai`

**Modelos soportados:**
- gpt-4
- gpt-4-turbo
- gpt-4o
- gpt-4o-mini
- gpt-3.5-turbo

**Configuración:**

```python
class OpenAIProvider(AIProviderInterface):
    def get_llm(self, model: str, temperature: float, 
                max_tokens: int, top_p: float) -> ChatOpenAI:
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p
        )

    def supports_interleaved_files(self) -> bool:
        return True
```

**Variable de entorno requerida:**
- `OPENAI_API_KEY`

---

### 2. Anthropic Provider (Claude)

**Identificador:** `claude`

**Modelos soportados:**
- claude-3-opus-20240229
- claude-3-sonnet-20240229
- claude-3-haiku-20240307
- claude-3-7-sonnet-20250219

**Configuración:**

```python
class AnthropicProvider(AIProviderInterface):
    def get_llm(self, model: str, temperature: float, 
                max_tokens: int, top_p: int) -> ChatAnthropic:
        return ChatAnthropic(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p
        )

    def supports_interleaved_files(self) -> bool:
        return True
```

**Variable de entorno requerida:**
- `ANTHROPIC_API_KEY`

---

### 3. Gemini Provider

**Identificador:** `gemini`

**Modelos soportados:**
- gemini-pro
- gemini-1.5-pro
- gemini-1.5-flash

**Configuración:**

```python
class GeminiProvider(AIProviderInterface):
    def get_llm(self, model: str, temperature: float, 
                max_tokens: int, top_p: int) -> ChatGoogleGenerativeAI:
        return ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            max_output_tokens=max_tokens,
            top_p=top_p,
            google_api_key=os.getenv("GOOGLE_GEMINI_API_KEY")
        )

    def supports_interleaved_files(self) -> bool:
        return True
```

**Variable de entorno requerida:**
- `GOOGLE_GEMINI_API_KEY`

---

### 4. DeepSeek Provider

**Identificador:** `deepseek`

**Modelos soportados:**
- deepseek-coder
- deepseek-chat

**Configuración:**

```python
class DeepseekProvider(AIProviderInterface):
    def get_llm(self, model: str, temperature: float, 
                max_tokens: int, top_p: float) -> Ollama:
        return Ollama(
            model=model,
            base_url=DEEP_SEEK_HOST,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p
        )

    def supports_interleaved_files(self) -> bool:
        return False  # DeepSeek no soporta archivos intercalados
```

**Variable de entorno requerida:**
- `HOST_DEEP_SEEK`

---

## Factory Pattern

### AIProviderFactory

```python
class AIProviderFactory:
    @staticmethod
    def get_provider(provider_name: str) -> AIProviderInterface:
        if provider_name == "openai":
            return OpenAIProvider()
        elif provider_name == "claude":
            return AnthropicProvider()
        elif provider_name == "deepseek":
            return DeepseekProvider()
        elif provider_name == "gemini":
            return GeminiProvider()
        else:
            raise ValueError(f"El proveedor de AI '{provider_name}' no está implementado")
```

## Uso en el Sistema

### Obtener un proveedor

```python
# Obtener el proveedor
provider = AIProviderFactory.get_provider("openai")

# Crear el LLM con configuración
llm = provider.get_llm(
    model="gpt-4",
    temperature=0.7,
    max_tokens=1000,
    top_p=1.0
)

# Verificar soporte de archivos
if provider.supports_interleaved_files():
    # Procesar con archivos
    pass
```

### Integración con ConversationManager

```python
async def process_conversation(self, request, agent_config):
    # El proveedor se obtiene de la configuración del agente
    ai_provider = AIProviderFactory.get_provider(agent_config.provider_ai)
    
    llm = ai_provider.get_llm(
        model=agent_config.model_ai,
        temperature=agent_config.preferences.temperature,
        max_tokens=agent_config.preferences.max_tokens,
        top_p=agent_config.preferences.top_p
    )
    
    # Usar el LLM en el procesador...
```

## Fallback Automático

El sistema implementa un fallback automático a Claude cuando hay errores:

```python
async def _fallback_with_anthropic(self, request, agent_config, history):
    anthropic_provider = AIProviderFactory.get_provider("claude")
    anthropic_llm = anthropic_provider.get_llm(
        model="claude-3-7-sonnet-20250219",
        temperature=agent_config.preferences.temperature,
        max_tokens=agent_config.preferences.max_tokens,
        top_p=agent_config.preferences.top_p
    )
    
    processor = SimpleProcessor(anthropic_llm, agent_config.prompt, history)
    return await processor.process(request, request.files, True)
```

## Agregar un Nuevo Proveedor

Para agregar un nuevo proveedor de IA:

1. Crear clase que implemente `AIProviderInterface`:

```python
# app/providers/new_provider.py
from app.providers.ai_provider_interface import AIProviderInterface

class NewProvider(AIProviderInterface):
    def get_llm(self, model: str, temperature: float, 
                max_tokens: int, top_p: float):
        return NewLLMClient(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p
        )

    def supports_interleaved_files(self) -> bool:
        return True  # o False según corresponda
```

2. Registrar en el Factory:

```python
# app/factories/ai_provider_factory.py
from app.providers.new_provider import NewProvider

class AIProviderFactory:
    @staticmethod
    def get_provider(provider_name: str) -> AIProviderInterface:
        # ... otros proveedores ...
        elif provider_name == "new_provider":
            return NewProvider()
```

3. Configurar variables de entorno necesarias.

## Parámetros de Configuración

| Parámetro | Tipo | Descripción | Default |
|-----------|------|-------------|---------|
| temperature | float | Creatividad de respuestas (0-2) | 0.7 |
| max_tokens | int | Máximo de tokens en respuesta | 1000 |
| top_p | float | Nucleus sampling (0-1) | 1.0 |

Estos parámetros se configuran por agente en el servicio `agent-config`.

# Procesadores de Conversación

Los procesadores son el corazón del sistema de conversación. Cada tipo de procesador maneja diferentes escenarios de interacción con la IA.

## Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                  ConversationProcessor (Base)                │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  - llm: BaseChatModel                                    ││
│  │  - context: str                                          ││
│  │  - history: List[str]                                    ││
│  │  + process(request, files, supports_interleaved)         ││
│  │  + _get_langsmith_config(request, processor_type)        ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                              ▲
              ┌───────────────┼───────────────┐
              │               │               │
     ┌────────┴────────┐ ┌────┴────┐ ┌───────┴───────┐
     │ SimpleProcessor │ │ Agent   │ │ MCPProcessor  │
     │                 │ │Processor│ │               │
     └─────────────────┘ └─────────┘ └───────────────┘
```

## ConversationProcessor (Base)

Clase base abstracta que define la interfaz común para todos los procesadores.

```python
class ConversationProcessor:
    def __init__(self, llm: BaseChatModel, context: str, history: List[str]):
        self.llm = llm
        self.context = context
        self.history = history

    def _get_langsmith_config(self, request, processor_type: str, **extra_metadata):
        """Genera configuración para trazabilidad con LangSmith"""
        return {
            "tags": [processor_type, f"agent_{request.agent_id}"],
            "metadata": {
                "agent_id": request.agent_id,
                "conversation_id": request.conversation_id,
                **extra_metadata
            }
        }

    async def process(self, query: str, files: Optional[List], 
                      supports_interleaved_files: bool) -> Dict[str, Any]:
        raise NotImplementedError
```

---

## SimpleProcessor

Procesador para conversaciones simples sin herramientas externas.

### Características

- Conversación directa con el LLM
- Soporte para archivos (imágenes)
- Parsing opcional de respuestas JSON
- Extracción automática de JSON de bloques markdown

### Flujo de Procesamiento

```
1. Construir mensaje del sistema (context + archivos + json_parser)
2. Añadir historial de conversación
3. Añadir mensaje del usuario
4. Invocar el LLM
5. Parsear respuesta (extraer JSON si aplica)
6. Retornar resultado estructurado
```

### Implementación

```python
class SimpleProcessor(ConversationProcessor):
    async def process(self, request: MessageRequest, 
                      files: Optional[List[Dict[str, str]]] = None,
                      supports_interleaved_files: bool = False) -> Dict[str, Any]:
        messages = []
        system_message = self.context or ""

        # Añadir referencias de archivos
        if files and not supports_interleaved_files:
            file_references = []
            for file in files:
                tag = 'image' if file.get('type') == 'image' else 'file'
                file_references.append(f"<{tag} url='{file['url']}'></{tag}>")
            system_message += "\n\n" + "\n".join(file_references)

        # Añadir instrucciones de JSON si se requiere
        if request.json_parser:
            format_instructions = json.dumps(request.json_parser, indent=2)
            system_message += (
                "\n\nIMPORTANT: Respond exclusively in JSON format...\n"
                f"{format_instructions}\n"
            )

        # Construir prompt
        messages.append(SystemMessage(content=system_message))
        messages.append(MessagesPlaceholder(variable_name="chat_history"))
        messages.append(HumanMessage(content=request.query))

        prompt = ChatPromptTemplate.from_messages(messages)
        
        return await self.generate_response(
            self.context, self.history, request.query, prompt
        )
```

### Uso

```python
processor = SimpleProcessor(llm, agent_config.prompt, history)
result = await processor.process(request, files, True)
# result = {"context": "...", "chat_history": [...], "input": "...", "text": "..."}
```

---

## AgentProcessor

Procesador para agentes con herramientas dinámicas (function calling).

### Características

- Soporte para herramientas personalizadas
- Uso de LangChain AgentExecutor
- Manejo de múltiples iteraciones
- Retorno de pasos intermedios

### Flujo de Procesamiento

```
1. Crear template de prompt con placeholders
2. Crear agente con tool_calling
3. Configurar AgentExecutor
4. Invocar el agente
5. Retornar resultado con pasos intermedios
```

### Implementación

```python
class AgentProcessor(ConversationProcessor):
    def __init__(self, llm: BaseChatModel, context: str, 
                 history: List[str], tools: List[Any]):
        super().__init__(llm, context, history)
        self.tools = tools

    async def process(self, request: MessageRequest, 
                      files: Optional[List[Dict[str, str]]] = None,
                      supports_interleaved_files: bool = False) -> Dict[str, Any]:
        
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", "{context}"),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = create_tool_calling_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt_template
        )

        agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=False,
            handle_parsing_errors=True,
            max_iterations=3,
            return_intermediate_steps=True
        )

        result = await agent_executor.ainvoke({
            "context": self.context or "",
            "chat_history": self.history,
            "input": request.query,
            "agent_scratchpad": ""
        })
        
        if "text" not in result and "output" in result:
            result["text"] = result["output"]
            
        return result
```

### Configuración de Herramientas

Las herramientas se generan dinámicamente desde la configuración del agente:

```python
tools = ToolGenerator.generate_tools(agent_config.tools or [])
if tools:
    processor = AgentProcessor(llm, agent_config.prompt, history, tools)
```

---

## MCPProcessor

Procesador para agentes que utilizan Model Context Protocol (MCP).

### Características

- Integración con servidores MCP
- Uso de LangGraph para agentes React
- Soporte para múltiples servidores MCP
- Extracción de información de herramientas

### Flujo de Procesamiento

```
1. Conectar con servidores MCP
2. Obtener herramientas disponibles
3. Crear agente React con LangGraph
4. Procesar mensajes
5. Extraer información de herramientas usadas
6. Retornar resultado con tool_result
```

### Implementación

```python
class MCPProcessor(ConversationProcessor):
    def __init__(self, llm: BaseChatModel, context: str, 
                 history: List[str], mcp_config: Dict[str, Any]):
        super().__init__(llm, context, history)
        self.mcp_config = mcp_config

    async def process(self, request: MessageRequest, 
                      files: Optional[List[Dict[str, str]]] = None,
                      supports_interleaved_files: bool = False) -> Dict[str, Any]:
        
        async with MultiServerMCPClient(self.mcp_config) as client:
            agent = create_react_agent(self.llm, client.get_tools())

            messages = []
            if self.context:
                messages.append({"role": "system", "content": self.context})
            
            if self.history:
                messages.extend(self.history)
            
            messages.append({"role": "user", "content": request.query})

            response = await agent.ainvoke({"messages": messages})

            # Extraer contenido de la respuesta
            content = self._extract_content(response)
            
            # Extraer información de herramientas
            tool_info = await self.get_tool_data(response)

            return {
                "context": self.context,
                "chat_history": self.history,
                "input": request.query,
                "text": content,
                "tool_result": tool_info
            }

    async def get_tool_data(self, response):
        """Extrae información de las herramientas utilizadas"""
        tool_messages = [
            msg for msg in response.get('messages', [])
            if getattr(msg, 'type', None) == 'tool'
        ]
        
        if tool_messages:
            last_tool = tool_messages[-1]
            return {
                "name": last_tool.name,
                "message": json.loads(last_tool.content)
            }
        return None
```

### Configuración MCP

El MCP se configura en la respuesta del agente:

```python
{
    "mcp_config": {
        "server1": {
            "url": "http://mcp-server:3000",
            "transport": "sse"
        }
    }
}
```

---

## Selección de Procesador

El `ConversationManager` selecciona el procesador apropiado:

```python
async def process_conversation(self, request, agent_config):
    ai_provider = AIProviderFactory.get_provider(agent_config.provider_ai)
    llm = ai_provider.get_llm(...)
    history = self.get_conversation_history(request.conversation_id)

    # Selección del procesador
    if agent_config.mcp_config:
        processor = MCPProcessor(llm, agent_config.prompt, history, agent_config.mcp_config)
    else:
        tools = ToolGenerator.generate_tools(agent_config.tools or [])
        if tools:
            processor = AgentProcessor(llm, agent_config.prompt, history, tools)
        else:
            processor = SimpleProcessor(llm, agent_config.prompt, history)

    return await processor.process(request, request.files, 
                                    ai_provider.supports_interleaved_files())
```

## Trazabilidad con LangSmith

Todos los procesadores incluyen configuración para LangSmith:

```python
config = self._get_langsmith_config(
    request,
    "simple_processor",  # o "agent_processor", "mcp_processor"
    has_json_parser=request.json_parser is not None,
    has_files=files is not None and len(files) > 0
)

result = await chain.ainvoke(input_data, config=config)
```

Esto permite:
- Ver trazas de cada request
- Identificar agentes por ID
- Depurar conversaciones específicas
- Analizar métricas de rendimiento

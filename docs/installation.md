# Instalación y Configuración

## Requisitos del Sistema

- Python 3.10 o superior
- pip (gestor de paquetes de Python)
- Docker (opcional, para despliegue containerizado)

## Instalación Local

### 1. Clonar el Repositorio

```bash
git clone <repository-url>
cd conversational-engine
```

### 2. Crear Entorno Virtual (Recomendado)

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# o
.\venv\Scripts\activate  # Windows
```

### 3. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar Variables de Entorno

Crear un archivo `.env` en la raíz del proyecto:

```bash
cp .env.example .env
```

Editar el archivo `.env` con tus credenciales (ver [Variables de Entorno](./environment-variables.md)).

### 5. Ejecutar el Servidor

```bash
python main.py
```

O usando uvicorn directamente:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Instalación con Docker

### 1. Construir la Imagen

```bash
docker build -t conversational-engine .
```

### 2. Ejecutar el Contenedor

```bash
docker run -p 8000:8000 --env-file .env conversational-engine
```

### Dockerfile

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "main.py"]
```

## Dependencias Principales

| Paquete | Versión | Descripción |
|---------|---------|-------------|
| fastapi | >=0.109.1 | Framework web asíncrono |
| pydantic | >=2.5.0 | Validación de datos |
| uvicorn | 0.24.0 | Servidor ASGI |
| httpx | >=0.24.0 | Cliente HTTP asíncrono |
| langchain-community | >=0.2.0 | Herramientas LangChain |
| langchain-openai | >=0.0.5 | Integración OpenAI |
| langchain-anthropic | - | Integración Anthropic |
| langchain-google-genai | - | Integración Google Gemini |
| langgraph | 0.3.31 | Grafos de agentes |
| langchain-mcp-adapters | 0.0.9 | Adaptadores MCP |
| fpdf | - | Generación de PDFs |
| beautifulsoup4 | - | Parsing HTML |
| Pillow | 10.3.0 | Procesamiento de imágenes |
| langsmith | - | Observabilidad de LLMs |

## Verificar Instalación

Una vez iniciado el servidor, verifica que funcione correctamente:

### Health Check

```bash
curl http://localhost:8000/api/ms/conversational-engine/health
```

Respuesta esperada:
```json
{"status": "OK"}
```

### Documentación API

Accede a la documentación interactiva:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Configuración para Desarrollo

### Hot Reload

Para desarrollo con recarga automática:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Debug Mode

Habilitar logging detallado añadiendo al `.env`:

```
ENVIRONMENT=development
```

## Solución de Problemas

### Error: ModuleNotFoundError

```bash
pip install -r requirements.txt --force-reinstall
```

### Error: Puerto 8000 en uso

```bash
# Encontrar proceso usando el puerto
lsof -i :8000

# Matar el proceso
kill -9 <PID>
```

### Error: Variables de entorno no encontradas

Verificar que el archivo `.env` existe y tiene las variables requeridas:

```bash
cat .env
```

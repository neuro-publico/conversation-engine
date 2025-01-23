
# Conversational Engine Microservice

This microservice is built using Python with FastAPI and communicates with external services like `agent-config` and AI providers to handle user queries. It utilizes the LangChain library to interact with the AI models and generate appropriate responses based on the agent configuration.

## Features

- **Handles User Queries:** The microservice receives a query from a user and processes it by calling the external `agent-config` service to retrieve the configuration of the agent.
- **Agent Configuration:** The microservice integrates with an external service (`agent-config`) to fetch the agent configuration based on the query context.
- **AI Interaction:** Once the agent configuration is retrieved, it uses LangChain to communicate with AI models and provides responses to user queries.
- **Handles Multiple Agent Types:** The service supports different types of agents, which can be configured according to the query context.

## Setup

1. Clone this repository.
2. Install the necessary dependencies using pip:

```bash
pip install -r requirements.txt
```

3. Run the FastAPI application:

```bash
uvicorn app:app --reload
```

4. The service will be running on `http://localhost:8000`.

## API Endpoints

### `POST /api/ms/conversational-agent/handle-message`

This endpoint is used to send a user query to the conversational agent and get a response based on the agent configuration.

#### Request Body

```json
{
  "query": "string", 
  "agent_id": "string (optional)",
  "parameter_prompt": "object (optional)",
  "conversation_id": "string (optional)",
  "metadata_filter": "object (optional)"
}
```

#### Example cURL Commands

1. **Query: "hola que vendes"**

```bash
curl --location 'http://localhost:8000/api/ms/conversational-agent/handle-message' --header 'Content-Type: application/json' --data-raw '{
    "query": "hola que vendes",
    "agent_id": "mi_primer_agente_base_seller_chat",
    "parameter_prompt": {
        "detail": {
            "store_name": "Tienda MundoTech",
            "store_phone": "+1-800-555-1234",
            "store_email": "contacto@mundotech.com",
            "store_website": "https://www.mundotech.com",
            "store_address": "Av. Principal 123, Ciudad Tecno, País Tech",
            "store_hours": {
                "monday_to_friday": "9:00 AM - 8:00 PM",
                "saturday": "10:00 AM - 6:00 PM",
                "sunday": "Cerrado"
            },
            "products": [
                {
                    "category": "Electrónicos",
                    "items": ["Laptops", "Tablets", "Smartphones", "Smartwatches", "Auriculares Bluetooth"]
                },
                {
                    "category": "Accesorios de Computación",
                    "items": ["Teclados mecánicos", "Ratones inalámbricos", "Monitores 4K", "Cables HDMI", "Bases de refrigeración"]
                },
                {
                    "category": "Hogar Inteligente",
                    "items": ["Asistentes de voz", "Cámaras de seguridad", "Enchufes inteligentes", "Luces LED inteligentes", "Termostatos inteligentes"]
                }
            ],
            "promotions": [
                "10% de descuento en laptops seleccionadas",
                "2x1 en auriculares Bluetooth",
                "Envío gratis en compras mayores a $100"
            ],
            "return_policy": "Aceptamos devoluciones dentro de los 30 días posteriores a la compra con recibo original. Los productos deben estar en condiciones originales.",
            "customer_service_hours": "Lunes a viernes de 9:00 AM a 6:00 PM",
            "social_media": {
                "facebook": "https://facebook.com/mundotech",
                "instagram": "https://instagram.com/mundotech",
                "twitter": "https://twitter.com/mundotech"
            }
        }
    },
    "conversation_id": "",
    "metadata_filter": null
}'
```

2. **Query: "ayudame con info para zapatos super start"**

```bash
curl --location 'http://localhost:8000/api/ms/conversational-agent/handle-message' --header 'Content-Type: application/json' --data '{
    "query": "ayudame con info para zapatos super start",
    "agent_id": "mi_primer_agente_info",
    "parameter_prompt": null,
    "conversation_id": "",
    "metadata_filter": null
}'
```

3. **Query: "quiero cambiar 2000mxn a usd"**

```bash
curl --location 'http://localhost:8000/api/ms/conversational-agent/handle-message' --header 'Content-Type: application/json' --data '{
    "query": "quiero cambiar 2000mxn a usd",
    "agent_id": null,
    "parameter_prompt": null,
    "conversation_id": "",
    "metadata_filter": null
}'
```

4. **Query: "cual es el precio de las supertart dolares en mxn son 200000"**

```bash
curl --location 'http://localhost:8000/api/ms/conversational-agent/handle-message' --header 'Content-Type: application/json' --data '{
    "query": "cual es el precio de las supertart dolares en mxn son 200000",
    "agent_id": "mi_primer_agente_deporte",
    "parameter_prompt": null,
    "conversation_id": "",
    "metadata_filter": null
}'
```

## External Services

- **Agent Config Service:** The `agent-config` microservice is responsible for retrieving the configuration of the agent based on the query type. This information is used to customize the response generation.
- **AI Providers:** The service utilizes LangChain to interact with various AI models and generate answers to user queries based on the agent configuration.

## Dependencies

- FastAPI
- LangChain
- Uvicorn
- Requests
- JSON

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


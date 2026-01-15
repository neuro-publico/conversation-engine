# Sistema de Scraping

El sistema de scraping permite extraer información de productos desde diferentes plataformas de e-commerce.

## Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                     ScrapingFactory                          │
│  ┌─────────────────────────────────────────────────────────┐│
│  │              get_scraper(url, country)                   ││
│  └─────────────────────────────────────────────────────────┘│
└──────────────────────────┬──────────────────────────────────┘
                           │
    ┌──────────┬───────────┼───────────┬──────────┐
    ▼          ▼           ▼           ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│ Amazon │ │AliExpr │ │ Dropi  │ │   CJ   │ │   IA   │
│Scraper │ │Scraper │ │Scraper │ │Scraper │ │Scraper │
└────────┘ └────────┘ └────────┘ └────────┘ └────────┘
```

## ScraperInterface

Interfaz base que todos los scrapers deben implementar:

```python
class ScraperInterface(ABC):
    @abstractmethod
    async def scrape(self, url: str, domain: str = None) -> Dict[str, Any]:
        """Extrae información de un producto desde su URL"""
        pass

    @abstractmethod
    async def scrape_direct(self, html: str) -> Dict[str, Any]:
        """Extrae información directamente desde HTML"""
        raise NotImplementedError
```

## ScrapingFactory

Factory que selecciona el scraper apropiado según la URL:

```python
class ScrapingFactory:
    def __init__(self, message_service: MessageServiceInterface = Depends()):
        self.message_service = message_service

    def get_scraper(self, url: str, country: str = "co") -> ScraperInterface:
        domain = urlparse(url).netloc.lower()

        if "amazon" in domain:
            return AmazonScraper()
        elif "aliexpress" in domain:
            return AliexpressScraper()
        elif "cjdropshipping" in domain:
            return CJScraper()
        elif "dropi" in domain:
            return DropiScraper(country=country)
        else:
            return IAScraper(message_service=self.message_service)
```

---

## AmazonScraper

Extrae productos de Amazon usando RapidAPI.

### Características

- Extracción de ASIN desde URL
- Información de precios y variantes
- Imágenes del producto
- Descripción y características

### Estructura de Respuesta

```json
{
  "data": {
    "provider_id": "amazon",
    "external_id": "B01234567",
    "name": "Nombre del producto",
    "description": "Descripción del producto",
    "external_sell_price": 29.99,
    "images": ["url1", "url2"],
    "variants": [
      {
        "provider_id": "amazon",
        "external_id": "B01234568",
        "name": "Nombre del producto",
        "images": ["url"],
        "variant_key": "color-blue-size-M",
        "attributes": [
          {"category_name": "Color", "value": "Blue"},
          {"category_name": "Size", "value": "M"}
        ]
      }
    ]
  }
}
```

### Patrones de Extracción de ASIN

```python
patterns = [
    r'/dp/([A-Z0-9]{10})',
    r'/gp/product/([A-Z0-9]{10})',
    r'/ASIN/([A-Z0-9]{10})',
    r'asin=([A-Z0-9]{10})',
    r'asin%3D([A-Z0-9]{10})'
]
```

---

## AliexpressScraper

Extrae productos de AliExpress usando RapidAPI.

### Características

- Extracción de Item ID desde URL
- Precios promocionales
- Múltiples imágenes
- Variantes con atributos

### Estructura de Respuesta

```json
{
  "data": {
    "provider_id": "aliexpress",
    "external_id": "1005001234567890",
    "name": "Nombre del producto",
    "description": "Propiedades del producto",
    "external_sell_price": 15.99,
    "images": ["url1", "url2"]
  }
}
```

### Extracción de Precios

```python
def _get_price(self, item_data: Dict[str, Any]) -> Optional[Decimal]:
    sku_data = item_data.get("sku", {})
    def_data = sku_data.get("def", {})
    
    # Precio promocional primero
    promotion_price = def_data.get("promotionPrice")
    if promotion_price:
        return self._parse_price(promotion_price)
    
    # Precio regular
    price = def_data.get("price")
    if isinstance(price, str) and " - " in price:
        price = price.split(" - ")[0]  # Tomar el menor
    return self._parse_price(price)
```

---

## DropiScraper

Extrae productos de la plataforma Dropi.

### Características

- Soporte multi-país (CO, MX, AR, CL, PE, PY, EC)
- Variantes con atributos
- Stock por almacén
- Precios sugeridos

### Configuración por País

```python
class DropiScraper(ScraperInterface):
    def __init__(self, country: str = "co"):
        self.country = country
```

### Estructura de Respuesta

```json
{
  "data": {
    "provider_id": "dropi",
    "external_id": "12345",
    "name": "Nombre del producto",
    "description": "Descripción limpia",
    "external_sell_price": 50000,
    "images": ["https://d39ru7awumhhs2.cloudfront.net/..."],
    "variants": [
      {
        "name": "Producto - Negro - L",
        "variant_key": "color-negro-talla-l",
        "price": 50000,
        "available": true,
        "images": ["url"],
        "attributes": [
          {"name": "Color", "value": "Negro"},
          {"name": "Talla", "value": "L"}
        ],
        "provider_id": "dropi",
        "external_id": "123",
        "external_sell_price": 50000,
        "external_suggested_sell_price": 80000
      }
    ]
  }
}
```

### Limpieza de Descripción

```python
def _get_description(self, product_data: Dict[str, Any]) -> str:
    html_description = product_data.get("description", "")
    # Remover tags HTML
    clean_text = re.sub(r'<[^>]+>', ' ', html_description)
    clean_text = clean_text.replace('<br>', '\n').strip()
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    return clean_text
```

---

## IAScraper

Scraper genérico que usa IA para extraer información de cualquier sitio.

### Características

- Funciona con cualquier sitio web
- Usa ScraperAPI para obtener HTML
- Procesa el HTML con un agente de IA
- Limpieza profunda de HTML

### Flujo de Procesamiento

```
1. Obtener HTML del sitio (ScraperAPI)
2. Limpiar HTML profundamente
3. Enviar a agente de IA para extracción
4. Parsear respuesta JSON
5. Normalizar datos
```

### Implementación

```python
class IAScraper(ScraperInterface):
    def __init__(self, message_service: MessageServiceInterface):
        self.message_service = message_service

    async def scrape(self, url: str, domain: str = None) -> Dict[str, Any]:
        client = ScraperAPIClient()
        
        if domain and "alibaba" in domain:
            html_content = await client.get_html(url)
        else:
            html_content = await client.get_html_lambda(url)
        
        # Limpiar HTML
        simplified_html = clean_html_deeply(html_content)

        # Enviar a agente de IA
        message_request = MessageRequest(
            query=f"provider_id={domain} . product_url={url} Product content: {simplified_html}",
            agent_id=SCRAPER_AGENT,
            conversation_id="",
        )

        result = await self.message_service.handle_message(message_request)
        
        # Parsear y normalizar
        data = json.loads(clean_json(result['text']))
        data['data']['external_sell_price'] = parse_price(data['data']['external_sell_price'])
        
        return data
```

---

## ProductScrapingService

Servicio que orquesta el scraping:

```python
class ProductScrapingService(ProductScrapingServiceInterface):
    def __init__(self, scraping_factory: ScrapingFactory = Depends()):
        self.scraping_factory = scraping_factory

    async def scrape_product(self, request: ProductScrapingRequest):
        url = str(request.product_url)
        domain = urlparse(url).netloc.lower()

        scraper = self.scraping_factory.get_scraper(url, country=request.country)
        return await scraper.scrape(url, domain)

    async def scrape_direct(self, html):
        scraper = self.scraping_factory.get_scraper("https://default-url.com")
        return await scraper.scrape_direct(html)
```

---

## Helper de Precios

Utilidad para parsear diferentes formatos de precio:

```python
def parse_price(price_str: Any) -> Optional[Decimal]:
    if isinstance(price_str, (int, float)):
        return Decimal(str(price_str))

    if isinstance(price_str, str):
        # Extraer números del string
        match = re.search(r'(\d+(?:\.\d+)?)', price_str.replace(",", ""))
        if match:
            return Decimal(match.group(1))
    
    return None
```

## Agregar Nuevo Scraper

1. Crear clase que implemente `ScraperInterface`:

```python
# app/scrapers/new_scraper.py
class NewScraper(ScraperInterface):
    async def scrape(self, url: str, domain: str = None) -> Dict[str, Any]:
        # Implementación específica
        pass

    async def scrape_direct(self, html: str) -> Dict[str, Any]:
        return {}
```

2. Registrar en ScrapingFactory:

```python
# app/factories/scraping_factory.py
elif "newsite" in domain:
    return NewScraper()
```

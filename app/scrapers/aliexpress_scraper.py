from app.scrapers.scraper_interface import ScraperInterface
from typing import Dict, Any, List, Optional, Tuple
from app.externals.aliexpress.aliexpress_client import get_item_detail
import re
from fastapi import HTTPException
from decimal import Decimal, InvalidOperation
from typing import Dict, Any

class AliexpressScraper(ScraperInterface):
    async def scrape_direct(self, html: str) -> Dict[str, Any]:
        return {}

    async def scrape(self, url: str, domain: str = None) -> Dict[str, Any]:
        item_id = self._extract_item_id(url)
        product_details = await get_item_detail(item_id)

        try:
            item_data = self._get_item_data(product_details)

            result = {
                "name": self._get_name(item_data),
                "description": self._get_description(item_data),
                "external_sell_price": self._get_price(item_data),
                "images": self._get_images(item_data)
            }

            variants = self._extract_variants(item_data)
            if variants:
                result["variants"] = variants

            response = {
                "provider_id": "aliexpress",
                "external_id": item_id,
                **result
            }

            return {"data": response}

        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Error procesando datos del producto: {str(e)}"
            )

    def _extract_item_id(self, url: str) -> str:
        pattern = r'item/(\d+)\.html'
        match = re.search(pattern, url)
        if match:
            return match.group(1)

        pattern = r'itemId=(\d+)'
        match = re.search(pattern, url)
        if match:
            return match.group(1)

        raise HTTPException(status_code=400, detail=f"No se pudo extraer el ID del producto de la URL: {url}")

    def _get_item_data(self, response: Dict[str, Any]) -> Dict[str, Any]:
        result = response.get("result", {})
        item_data = result.get("item", {})
        if not item_data:
            raise ValueError("No se encontraron datos del producto en la respuesta")
        return item_data

    def _get_name(self, item_data: Dict[str, Any]) -> str:
        return item_data.get("title", "")

    def _get_description(self, item_data: Dict[str, Any]) -> str:
        description = ""
        description_data = item_data.get("description", {})
        if description_data:
            # Intentamos extraer el texto de la descripción HTML
            html_content = description_data.get("html", "")
            if html_content:
                # Simplificación básica - podría mejorarse con una biblioteca HTML
                description = re.sub(r'<[^>]+>', ' ', html_content)
                description = re.sub(r'\s+', ' ', description).strip()

        # Si no hay descripción, intentamos usar las propiedades
        if not description and "properties" in item_data:
            properties = item_data.get("properties", {}).get("list", [])
            if properties:
                description = "\n".join([f"{prop.get('name')}: {prop.get('value')}" for prop in properties])

        return description

    def _get_price(self, item_data: Dict[str, Any]) -> Optional[Decimal]:
        sku_data = item_data.get("sku", {})
        if not sku_data:
            return None

        # Intentar obtener el precio de promoción primero
        def_data = sku_data.get("def", {})
        if def_data:
            promotion_price = def_data.get("promotionPrice")
            if promotion_price:
                return self._parse_price(promotion_price)

            price = def_data.get("price")
            if price:
                # Si el precio es un rango (ej: "3.55 - 3.87"), tomamos el valor más bajo
                if isinstance(price, str) and " - " in price:
                    price = price.split(" - ")[0]
                return self._parse_price(price)

        # Si no hay precio en def, intentamos con la primera variante
        base_variants = sku_data.get("base", [])
        if base_variants and len(base_variants) > 0:
            first_variant = base_variants[0]
            promotion_price = first_variant.get("promotionPrice")
            if promotion_price:
                return self._parse_price(promotion_price)

            price = first_variant.get("price")
            if price:
                return self._parse_price(price)

        return None

    def _parse_price(self, price_str: Any) -> Optional[Decimal]:
        if isinstance(price_str, (int, float)):
            return Decimal(str(price_str))

        if isinstance(price_str, str):
            match = re.search(r'(\d+(?:\.\d+)?)', price_str.replace(",", ""))
            if match:
                try:
                    return Decimal(match.group(1))
                except InvalidOperation:
                    return None
        return None

    def _get_images(self, item_data: Dict[str, Any]) -> List[str]:
        images = []

        # Obtener imágenes principales
        main_images = item_data.get("images", [])
        if main_images:
            # Asegurarse de que las URLs sean absolutas
            images = [self._ensure_absolute_url(img) for img in main_images]

        # Si no hay imágenes principales, intentar con imágenes de descripción
        if not images and "description" in item_data:
            desc_images = item_data.get("description", {}).get("images", [])
            if desc_images:
                images = [self._ensure_absolute_url(img) for img in desc_images]

        return images

    def _ensure_absolute_url(self, url: str) -> str:
        """Asegura que la URL sea absoluta agregando el protocolo si es necesario."""
        if url.startswith("//"):
            return f"https:{url}"
        return url

    def _extract_variants(self, item_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        variants = []
        sku_data = item_data.get("sku", {})

        if not sku_data or "base" not in sku_data or "props" not in sku_data:
            return []

        base_variants = sku_data.get("base", [])
        props = sku_data.get("props", [])
        product_title = item_data.get("title", "")

        # Crear mapeo de propiedades
        prop_map = self._create_property_map(props)

        # Procesar cada variante
        for variant in base_variants:
            sku_id = variant.get("skuId")
            sku_attr = variant.get("skuAttr", "")

            # Extraer atributos y imágenes de la variante
            attributes, variant_images = self._process_variant_attributes(sku_attr, prop_map)

            # Si no hay imágenes específicas de la variante, usar las imágenes principales
            if not variant_images:
                main_images = self._get_images(item_data)
                if main_images:
                    variant_images = [main_images[0]]

            # Crear clave de variante
            variant_key = "-".join([attr["value"] for attr in attributes])

            variant_info = {
                "provider_id": "aliexpress",
                "external_id": sku_id,
                "name": product_title,
                "images": variant_images,
                "variant_key": variant_key,
                "attributes": attributes
            }

            variants.append(variant_info)

        return variants

    def _create_property_map(self, props: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
        """Crea un mapa de propiedades para facilitar la búsqueda de atributos de variantes."""
        prop_map = {}
        for prop in props:
            prop_id = prop.get("pid")
            prop_name = prop.get("name")
            values = {}
            for val in prop.get("values", []):
                values[val.get("vid")] = {
                    "name": val.get("name"),
                    "image": val.get("image", "")
                }
            prop_map[prop_id] = {
                "name": prop_name,
                "values": values
            }
        return prop_map

    def _process_variant_attributes(self, sku_attr: str, prop_map: Dict[int, Dict[str, Any]]) -> Tuple[
        List[Dict[str, Any]], List[str]]:
        """Procesa los atributos de una variante y extrae imágenes relacionadas."""
        attributes = []
        variant_images = []

        # Atributos a ignorar
        ignored_attributes = ["Ships From", "ship from"]

        if not sku_attr:
            return attributes, variant_images

        # Parsear skuAttr (formato: "pid:vid;pid:vid")
        attr_parts = sku_attr.split(";")
        for part in attr_parts:
            if ":" not in part:
                continue

            pid_vid = part.split(":")
            if len(pid_vid) != 2:
                continue

            try:
                pid = int(pid_vid[0])
                vid_raw = pid_vid[1]

                # Extraer el vid (puede tener formato "vid#name")
                vid = vid_raw
                if "#" in vid_raw:
                    vid = vid_raw.split("#")[0]

                try:
                    vid = int(vid)
                except:
                    pass

                if pid in prop_map and vid in prop_map[pid]["values"]:
                    prop_info = prop_map[pid]
                    value_info = prop_info["values"][vid]

                    # Ignorar atributos de envío
                    if prop_info["name"] not in ignored_attributes:
                        attributes.append({
                            "category_name": prop_info["name"],
                            "value": value_info["name"]
                        })

                    # Agregar imagen de la variante si existe
                    if value_info["image"]:
                        variant_images.append(self._ensure_absolute_url(value_info["image"]))
            except:
                continue

        return attributes, variant_images

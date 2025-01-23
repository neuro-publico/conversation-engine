from typing import Dict
import requests


class BaseRequestor:
    @staticmethod
    def replace_placeholders(text: str, params: dict) -> str:
        """Reemplaza los placeholders en el formato {variable} con valores reales"""
        for key, value in params.items():
            placeholder = f"{{{key}}}"
            if isinstance(text, str) and placeholder in text:
                text = text.replace(placeholder, str(value))
        return text

    @classmethod
    def prepare_request_data(cls, config: dict, params: dict) -> dict:
        """Prepara los datos de la petición reemplazando los placeholders"""
        request_data = {
            'url': config['api'],
            'method': config['method'],
            'headers': {},
            'body': config.get('body', {})
        }

        # Procesar headers
        for header in config.get('headers', []):
            key = header['key']
            value = cls.replace_placeholders(header['value'], params)
            request_data['headers'][key] = value

        # Procesar body
        if isinstance(request_data['body'], dict):
            processed_body = {}
            for key, value in request_data['body'].items():
                processed_body[key] = cls.replace_placeholders(value, params)
            request_data['body'] = processed_body

        # Procesar URL
        request_data['url'] = cls.replace_placeholders(request_data['url'], params)

        # Procesar query params si existen
        if 'query_params' in config:
            processed_params = {}
            for key, value in config['query_params'].items():
                processed_params[key] = cls.replace_placeholders(value, params)
            request_data['params'] = processed_params

        return request_data

    @classmethod
    def execute_request(cls, config: Dict, params: Dict) -> Dict:
        """Ejecuta la petición HTTP y retorna el resultado"""
        try:
            request_data = cls.prepare_request_data(config, params)

            response = requests.request(
                method=request_data['method'],
                url=request_data['url'],
                headers=request_data['headers'],
                json=request_data.get('body'),
                params=request_data.get('params', {})
            )

            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"Error en la petición: {str(e)}"}
        except Exception as e:
            return {"error": f"Error inesperado: {str(e)}"}

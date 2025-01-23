from typing import List
from langchain_core.tools import Tool, StructuredTool
from pydantic import create_model, Field
import json
import os
from app.data.currency_data import CURRENCY_DATA


class ToolGenerator:
    @staticmethod
    def load_tools_config() -> dict:
        """Carga la configuración de todas las herramientas desde el JSON"""
        config_path = os.path.join(os.path.dirname(__file__), '../data/tools.json')
        with open(config_path, 'r') as f:
            return json.load(f)

    @staticmethod
    def create_tool_function(tool_config: dict):
        #TODO REQUEST GENERIC
        """Crea la función de implementación basada en el tipo de herramienta"""
        implementation = tool_config['implementation']

        if implementation['type'] == 'currency_conversion':
            def tool_function(**kwargs):
                amount = kwargs['amount']
                from_currency = kwargs['from_currency'].upper()
                to_currency = kwargs['to_currency'].upper()

                if from_currency == to_currency:
                    return f"{amount} {from_currency}"

                if from_currency not in CURRENCY_DATA["conversiones"] or \
                        to_currency not in CURRENCY_DATA["conversiones"][from_currency]:
                    return "Moneda no soportada"

                rate = CURRENCY_DATA["conversiones"][from_currency][to_currency]
                converted_amount = amount * rate

                return {"tool_result": {"origin": f"{amount} {from_currency}",
                                        "to": f"{converted_amount:.2f} {to_currency}"}}

            return tool_function

        # Aquí puedes agregar más tipos de implementaciones
        return None

    @classmethod
    def generate_tools(cls) -> List[StructuredTool]:
        """Genera todas las herramientas desde la configuración"""
        tools_config = cls.load_tools_config()
        tools = []

        for tool_config in tools_config['tools']:
            # Crear el modelo Pydantic para los argumentos
            field_definitions = {}
            for name, details in tool_config['parameters']['properties'].items():
                python_type = float if details['type'] == 'number' else str
                field_definitions[name] = (
                    python_type,
                    Field(..., description=details['description'])
                )

            args_schema = create_model(
                f"{tool_config['name'].title()}Input",
                **field_definitions
            )

            # Crear la función de implementación
            func = cls.create_tool_function(tool_config)

            # Crear la herramienta
            tool = StructuredTool(
                name=tool_config['name'],
                description=tool_config['description'],
                func=func,
                args_schema=args_schema
            )

            tools.append(tool)

        return tools

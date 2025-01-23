from typing import List, Optional
from langchain_core.tools import StructuredTool
from pydantic import create_model, Field

from app.requestors.base_requestor import BaseRequestor


class ToolGenerator:
    @classmethod
    def create_tool_function(cls, tool_config: dict):
        """Crea la función de implementación basada en la configuración de la herramienta"""
        config = tool_config['config']

        def tool_function(**kwargs):
            return {"tool_result": BaseRequestor.execute_request(config, kwargs)}

        return tool_function

    @classmethod
    def generate_tools(cls, tools: Optional[List[dict]]) -> List[StructuredTool]:
        """Genera una lista de herramientas estructuradas a partir de configuraciones"""
        structured_tools = []

        if not tools:
            return []

        for tool_config in tools:
            # Crear el modelo Pydantic para los argumentos
            field_definitions = {}
            for prop in tool_config['config']['properties']:
                field_definitions[prop['name']] = (
                    str,
                    Field(..., description=prop['description'])
                )

            args_schema = create_model(
                f"{tool_config['tool_name'].title()}Input",
                **field_definitions
            )

            # Crear la herramienta
            tool = StructuredTool(
                name=tool_config['tool_name'],
                description=tool_config['description'],
                func=cls.create_tool_function(tool_config),
                args_schema=args_schema
            )

            structured_tools.append(tool)

        return structured_tools

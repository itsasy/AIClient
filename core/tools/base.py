from __future__ import annotations

from abc import ABC, abstractmethod

from typing import Any


class Tool(ABC):
    """
    Contrato base para herramientas del sistema.

    Una Tool representa una capacidad operacional
    de infraestructura.

    Responsabilidades:

    - Ejecutar operaciones externas.
    - Interactuar con sistema operativo.
    - Manejar recursos externos.

    No:

    - Decide flujos.
    - Crea planes.
    - Ejecuta Skills.
    - Gestiona contexto global.
    """

    name: str = "base"

    description: str = ""

    version: str = "1.0"

    capabilities: tuple[str, ...] = ()

    def get_metadata(
        self,
    ) -> dict[str, Any]:

        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "capabilities": list(
                self.capabilities,
            ),
        }

    def get_schema(self) -> dict[str, Any]:
        """
        Devuelve el schema de la herramienta en formato OpenAI JSON Schema.
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }

    @abstractmethod
    def execute(
        self,
        *args,
        **kwargs,
    ) -> dict[str, Any]:

        raise NotImplementedError

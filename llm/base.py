from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """
    Contrato base para proveedores LLM.

    Cada proveedor debe implementar:

    - generate()
    """

    name: str = "base"

    @abstractmethod
    def generate(
        self,
        prompt: str,
        **kwargs: Any,
    ) -> str:
        """
        Genera una respuesta utilizando el proveedor LLM.

        Args:
            prompt:
                Instrucción enviada al modelo.

            kwargs:
                Parámetros adicionales del proveedor:
                - temperature
                - max_tokens
                - model
                - opciones específicas.

        Returns:
            Texto generado por el modelo.
        """

        raise NotImplementedError

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """
    Contrato base para todos los proveedores LLM.

    El ProviderManager es responsable de:
        - seleccionar el provider;
        - ejecutar fallback;
        - administrar instancias;
        - recolectar métricas.

    El provider es responsable únicamente de:
        - comunicarse con su API;
        - traducir errores de su SDK;
        - devolver texto generado.
    """

    name: str = "base"

    @abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> str:
        """
        Genera contenido mediante el proveedor.

        Args:
            prompt:
                Prompt principal enviado al modelo.

            model:
                Modelo específico solicitado.
                Si es None, utiliza el modelo configurado
                por el provider.

            system_prompt:
                Instrucción de sistema opcional.

            temperature:
                Temperatura de generación.

            max_tokens:
                Máximo de tokens de salida.

            kwargs:
                Parámetros específicos del proveedor.

        Returns:
            Texto generado.

        Raises:
            ProviderError:
                Para errores normalizados de proveedor.
        """
        raise NotImplementedError

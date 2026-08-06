from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Skill(ABC):
    """
    Contrato base de una Skill.

    Una Skill representa una capacidad ejecutable.

    El Runtime es responsable de:
    - Planificación.
    - Contexto.
    - Lifecycle.
    - Errores.
    - Retries.

    La Skill solamente ejecuta una capacidad concreta.
    """

    name: str = "base"

    description: str = ""

    version: str = "1.0"

    capabilities: list[str] = []

    @abstractmethod
    def execute(
        self,
        **kwargs: Any,
    ) -> Any:
        """
        Ejecuta la capacidad.

        Los argumentos vienen desde ExecutionStep.params.

        Puede recibir:
        - parámetros específicos.
        - context.
        - plan.
        - step.

        mediante kwargs.
        """

        raise NotImplementedError

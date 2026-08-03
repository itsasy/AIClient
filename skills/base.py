from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Skill(ABC):
    """
    Contrato base de todas las Skills.

    Una Skill representa una capacidad ejecutable
    dentro del sistema.

    Flujo:

    Agent
      |
      v
    SkillRuntime
      |
      v
    Skill
      |
      v
    execute()
    """

    name: str = "base"

    description: str = ""

    version: str = "1.0"

    @abstractmethod
    def execute(
        self,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Ejecuta la capacidad.

        Todas las skills deben devolver:

        {
            "ok": bool,
            "result": Any,
            "error": str | None
        }
        """

        raise NotImplementedError

    def validate(
        self,
        **kwargs: Any,
    ) -> list[str]:
        """
        Validación previa opcional.
        """

        return []

    def metadata(self) -> dict[str, Any]:
        """
        Información pública de la skill.
        """

        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
        }

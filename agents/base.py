from __future__ import annotations

from abc import ABC, abstractmethod

from typing import Any

from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep


class Agent(ABC):
    """
    Contrato base para agentes.

    Un Agent ejecuta una intención
    representada en un ExecutionPlan.

    No:

    - Construye planes.
    - Gestiona lifecycle.
    - Decide ejecución.
    - Resuelve otros agentes.
    """

    name: str = ""

    description: str = ""

    version: str = "1.0.0"

    aliases: tuple[str, ...] = ()

    capabilities: tuple[str, ...] = ()

    # ==================================================
    # Initialization
    # ==================================================

    def __init_subclass__(
        cls,
        **kwargs,
    ) -> None:

        super().__init_subclass__(
            **kwargs,
        )

        if not getattr(
            cls,
            "name",
            None,
        ):

            raise TypeError(
                f"{cls.__name__} debe definir name",
            )

    # ==================================================
    # Normalization
    # ==================================================

    @staticmethod
    def normalize(
        value: str | None,
    ) -> str:

        if not value:

            return ""

        return (
            value.lower()
            .strip()
            .replace(
                "-",
                "_",
            )
            .replace(
                " ",
                "_",
            )
        )

    # ==================================================
    # Validation
    # ==================================================

    @classmethod
    def validate_definition(
        cls,
    ) -> list[str]:

        errors: list[str] = []

        if not cls.name.strip():

            errors.append(
                "Agent sin nombre",
            )

        if not isinstance(
            cls.aliases,
            tuple,
        ):

            errors.append(
                "aliases debe ser tuple",
            )

        if not isinstance(
            cls.capabilities,
            tuple,
        ):

            errors.append(
                "capabilities debe ser tuple",
            )

        return errors

    def validate_plan(
        self,
        plan: ExecutionPlan,
    ) -> list[str]:

        return []

    def validate_step(
        self,
        step: ExecutionStep,
    ) -> list[str]:

        warnings: list[str] = []

        requested = self.normalize(
            step.unit_name,
        )

        current = self.normalize(
            self.name,
        )

        aliases = {self.normalize(alias) for alias in self.aliases}

        if requested and requested != current and requested not in aliases:

            warnings.append(f"Step apunta a '{step.unit_name}', " f"Agent activo '{self.name}'.")

        return warnings

    # ==================================================
    # Metadata
    # ==================================================

    def metadata(
        self,
    ) -> dict[str, Any]:

        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "aliases": list(self.aliases),
            "capabilities": list(self.capabilities),
        }

    def get_metadata(
        self,
    ) -> dict[str, Any]:

        return self.metadata()

    # ==================================================
    # Capabilities
    # ==================================================

    def supports(
        self,
        capability: str,
    ) -> bool:

        target = self.normalize(
            capability,
        )

        if not target:

            return False

        return target in {self.normalize(item) for item in self.capabilities}

    # ==================================================
    # Execution
    # ==================================================

    @abstractmethod
    def process(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any] | None = None,
    ) -> Any:

        raise NotImplementedError("Los agentes deben implementar process()")

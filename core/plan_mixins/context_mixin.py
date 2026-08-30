from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from core.execution_step import ExecutionStep

class PlanContextMixin:
    def _normalize_context_requirements(self) -> None:
        normalized: dict[str, bool] = {}

        for provider, required in self.context_requirements.items():
            if not isinstance(provider, str):
                raise ValueError("Los nombres de providers de contexto " "deben ser strings.")

            normalized_provider = provider.lower().strip()

            if not normalized_provider:
                raise ValueError("El nombre del provider de contexto " "no puede estar vacío.")

            if not isinstance(required, bool):
                raise ValueError(f"context_requirements.{provider} " "debe ser booleano.")

            normalized[normalized_provider] = required

        self.context_requirements = normalized

    def requires_context(
        self,
        provider: str,
    ) -> bool:
        if not isinstance(provider, str):
            return False

        provider = provider.lower().strip()

        if not provider:
            return False

        return bool(
            self.context_requirements.get(
                provider,
                False,
            )
        )

    def set_context_requirement(
        self,
        provider: str,
        required: bool,
    ) -> None:
        if not isinstance(provider, str):
            raise ValueError("El provider de contexto debe ser un string.")

        provider = provider.lower().strip()

        if not provider:
            raise ValueError("El provider de contexto no puede estar vacío.")

        if not isinstance(required, bool):
            raise ValueError("required debe ser booleano.")

        self.context_requirements[provider] = required

    def required_context_providers(self) -> list[str]:
        """API oficial para ContextManager."""
        requirements = getattr(self, "context_requirements", None) or {}
        if not isinstance(requirements, dict):
            return []
        return [key for key, required in requirements.items() if required]


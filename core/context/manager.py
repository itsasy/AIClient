from __future__ import annotations

import logging

from typing import Any

from core.execution_plan import ExecutionPlan

logger = logging.getLogger(__name__)


class ContextManager:
    """
    Constructor central de contexto de ejecución.

    Responsabilidades:

    - Resolver proveedores de contexto.
    - Construir contexto para ExecutionPlan.
    - Registrar contexto cargado.

    No:

    - Ejecuta Agents.
    - Ejecuta Skills.
    - Gestiona memoria persistente.
    - Decide qué contexto necesita un plan.
    """

    name = "context_manager"

    def __init__(
        self,
        providers: dict[str, Any] | None = None,
    ) -> None:

        self.providers: dict[str, Any] = providers or {}

    # ==================================================
    # Public API
    # ==================================================

    def build(
        self,
        plan: ExecutionPlan,
    ) -> dict[str, Any]:

        if not isinstance(
            plan,
            ExecutionPlan,
        ):

            raise TypeError(
                "ContextManager requiere ExecutionPlan",
            )

        context: dict[str, Any] = {}

        for provider_name in plan.context_requirements:

            try:

                value = self._resolve_provider(
                    provider_name,
                    plan,
                )

                if value is not None:

                    context[provider_name] = value

            except Exception:

                logger.exception(
                    "Error cargando contexto provider=%s",
                    provider_name,
                )

        plan.loaded_context = context.copy()

        return context

    # ==================================================
    # Provider management
    # ==================================================

    def register(
        self,
        name: str,
        provider: Any,
    ) -> None:

        if not name:

            raise ValueError(
                "Provider requiere nombre",
            )

        self.providers[self._normalize(name)] = provider

    def unregister(
        self,
        name: str,
    ) -> None:

        self.providers.pop(
            self._normalize(name),
            None,
        )

    # ==================================================
    # Resolution
    # ==================================================

    def _resolve_provider(
        self,
        name: str,
        plan: ExecutionPlan,
    ) -> Any:

        key = self._normalize(
            name,
        )

        provider = self.providers.get(
            key,
        )

        if provider is None:

            logger.debug(
                "Provider no disponible=%s",
                key,
            )

            return None

        if callable(provider):

            return provider(
                plan,
            )

        return provider

    # ==================================================
    # Helpers
    # ==================================================

    def _normalize(
        self,
        value: str,
    ) -> str:

        return value.lower().strip().replace("-", "_").replace(" ", "_")

    # ==================================================
    # Information
    # ==================================================

    def available(
        self,
    ) -> list[str]:

        return sorted(
            self.providers.keys(),
        )

    def contains(
        self,
        name: str,
    ) -> bool:

        return self._normalize(name) in self.providers

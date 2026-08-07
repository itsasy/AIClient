from __future__ import annotations

import logging

from typing import Any, Protocol

logger = logging.getLogger(__name__)


class ContextProvider(Protocol):
    """
    Contrato mínimo para proveedores de contexto.
    """

    def load(
        self,
        request: dict[str, Any],
    ) -> dict[str, Any]: ...


class ContextManager:
    """
    Gestiona carga y composición de contexto.

    Responsabilidades:

    - Resolver providers.
    - Cargar contexto requerido.
    - Unificar resultados.
    - Preparar execution_context.

    No:

    - Ejecuta tareas.
    - Modifica planes.
    - Gestiona memoria interna.
    - Decide estrategia LLM.
    """

    # ==================================================
    # Initialization
    # ==================================================

    def __init__(
        self,
        providers: dict[str, ContextProvider] | None = None,
    ):
        self.providers = providers or {}

    # ==================================================
    # Provider registry
    # ==================================================

    def register(
        self,
        name: str,
        provider: ContextProvider,
    ) -> None:

        key = self.normalize_name(
            name,
        )

        self.providers[key] = provider

    def has_provider(
        self,
        name: str,
    ) -> bool:

        return self.normalize_name(name) in self.providers

    # ==================================================
    # Public API
    # ==================================================

    def build(
        self,
        requirements: list[str],
        request: dict[str, Any] | None = None,
    ) -> dict[str, Any]:

        request = request or {}

        context: dict[str, Any] = {}

        for requirement in requirements:

            provider_name = self.normalize_name(
                requirement,
            )

            provider = self.providers.get(
                provider_name,
            )

            if not provider:

                logger.warning(
                    "Context provider no encontrado: %s",
                    provider_name,
                )

                continue

            try:

                data = provider.load(
                    request,
                )

                context[provider_name] = data or {}

            except Exception as exc:

                logger.exception(
                    "Error cargando contexto provider=%s",
                    provider_name,
                )

                context[provider_name] = {
                    "error": str(exc),
                }

        return context

    # ==================================================
    # Execution integration
    # ==================================================

    def attach_to_plan(
        self,
        plan: Any,
        request: dict[str, Any] | None = None,
    ) -> dict[str, Any]:

        context = self.build(
            requirements=plan.context_requirements,
            request=request,
        )

        plan.loaded_context = context

        plan.execution_context.update(
            context,
        )

        return context

    # ==================================================
    # Helpers
    # ==================================================

    @staticmethod
    def normalize_name(
        name: str,
    ) -> str:

        if not name:

            return ""

        return (
            name.lower()
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

    def available_providers(
        self,
    ) -> list[str]:

        return sorted(
            self.providers.keys(),
        )

    # ==================================================
    # Serialization
    # ==================================================

    def describe(
        self,
    ) -> dict[str, Any]:

        return {
            "providers": self.available_providers(),
        }

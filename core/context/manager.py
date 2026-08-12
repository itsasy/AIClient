from __future__ import annotations

import logging
from copy import deepcopy
from typing import Any

from core.context.base import BaseContextProvider
from core.context.documents_provider import DocumentsProvider
from core.context.engram_provider import EngramProvider
from core.context.gentleman_provider import GentlemanProvider
from core.context.memory_provider import MemoryProvider
from core.context.obsidian_provider import ObsidianProvider
from core.context.project_provider import ProjectProvider
from core.context.registry import ContextRegistry
from core.context.spec_provider import SpecProvider
from core.context.standards_provider import StandardsProvider
from core.context.swarmforge_provider import SwarmForgeProvider

logger = logging.getLogger(__name__)


class ContextManager:
    """
    Construye y controla el contexto de ejecución.

    Responsabilidades:
    - Resolver providers mediante ContextRegistry.
    - Cargar contexto bajo demanda.
    - Mantener el contexto de runtime.
    - Integrar los resultados de los providers.
    - Construir vistas específicas para Agents.

    No:
    - Decide la intención.
    - Construye ExecutionPlans.
    - Ejecuta Agents.
    - Ejecuta Skills.
    - Construye prompts LLM.
    - Ejecuta herramientas.
    - Gestiona el lifecycle de ejecución.
    """

    DEFAULT_PROVIDERS = (
        ProjectProvider,
        EngramProvider,
        MemoryProvider,
        ObsidianProvider,
        GentlemanProvider,
        StandardsProvider,
        DocumentsProvider,
        SpecProvider,
        SwarmForgeProvider,
    )

    def __init__(
        self,
        registry: ContextRegistry | None = None,
    ) -> None:
        self.registry = registry or ContextRegistry()

        self._register_defaults()

    def _register_defaults(self) -> None:
        """
        Registra los providers por defecto.

        Los providers ya registrados no se sobrescriben.
        """

        for provider_class in self.DEFAULT_PROVIDERS:

            if self.registry.has(provider_class.key):
                continue

            self.registry.register(provider_class)

    def build(
        self,
        plan: Any,
        step: Any | None = None,
        existing_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Construye el contexto requerido para una ejecución.

        El flujo es:

            ExecutionPlan
                ↓
            required_context_providers()
                ↓
            ContextRegistry
                ↓
            Provider.load()
                ↓
            ContextManager integra resultado
                ↓
            Contexto acumulado

        Los providers nunca mutan directamente el contexto.
        """

        context: dict[str, Any] = deepcopy(existing_context or {})

        execution = context.setdefault(
            "execution",
            {},
        )

        execution.update(
            {
                "plan_id": getattr(
                    plan,
                    "id",
                    None,
                ),
                "intent": getattr(
                    plan,
                    "intent",
                    None,
                ),
                "original_task": getattr(
                    plan,
                    "original_task",
                    None,
                ),
                "execution_mode": getattr(
                    plan,
                    "execution_mode",
                    None,
                ),
            }
        )

        if step is not None:
            execution["current_step"] = {
                "id": getattr(
                    step,
                    "id",
                    None,
                ),
                "unit_type": getattr(
                    step,
                    "unit_type",
                    None,
                ),
                "unit_name": getattr(
                    step,
                    "unit_name",
                    None,
                ),
                "description": getattr(
                    step,
                    "description",
                    None,
                ),
                "params": dict(
                    getattr(
                        step,
                        "params",
                        {},
                    )
                    or {}
                ),
                "depends_on": list(
                    getattr(
                        step,
                        "depends_on",
                        [],
                    )
                    or []
                ),
            }

        if plan is None:
            return context

        # Preferir la API pública del ExecutionPlan.
        #
        # Esto evita que ContextManager conozca directamente
        # la estructura interna de context_requirements.
        if hasattr(
            plan,
            "required_context_providers",
        ):
            provider_keys = plan.required_context_providers()

        else:
            # Fallback defensivo para compatibilidad con objetos
            # que todavía expongan únicamente context_requirements.
            requirements = (
                getattr(
                    plan,
                    "context_requirements",
                    {},
                )
                or {}
            )

            provider_keys = [key for key, required in requirements.items() if required]

        for key in provider_keys:

            provider = self.registry.get(key)

            if provider is None:
                logger.warning(
                    "Context provider no registrado: %s",
                    key,
                )
                continue

            try:
                data = provider.load(
                    plan,
                    context,
                )

                if not data:
                    continue

                # ContextManager es el único responsable
                # de integrar el resultado del provider.
                context[key] = data

                logger.debug(
                    "Contexto cargado: %s",
                    key,
                )

            except Exception:
                logger.exception(
                    "Error cargando context provider=%s",
                    key,
                )

        return context

    def record_step_result(
        self,
        context: dict[str, Any],
        step: Any,
        result: Any,
    ) -> None:
        """
        Registra el resultado de un step dentro del runtime context.
        """

        execution = context.setdefault(
            "execution",
            {},
        )

        steps = execution.setdefault(
            "steps",
            {},
        )

        step_id = getattr(
            step,
            "id",
            None,
        )

        if not step_id:
            return

        steps[step_id] = {
            "id": step_id,
            "unit_type": getattr(
                step,
                "unit_type",
                None,
            ),
            "unit_name": getattr(
                step,
                "unit_name",
                None,
            ),
            "description": getattr(
                step,
                "description",
                None,
            ),
            "status": getattr(
                result,
                "status",
                None,
            ),
            "result": getattr(
                result,
                "result",
                result,
            ),
            "error": getattr(
                result,
                "error",
                None,
            ),
        }

    def get_dependency_results(
        self,
        context: dict[str, Any],
        step: Any,
    ) -> dict[str, Any]:
        """
        Obtiene los resultados producidos por los steps
        de los que depende el step actual.
        """

        execution = context.get(
            "execution",
            {},
        )

        steps = execution.get(
            "steps",
            {},
        )

        result = {}

        for dependency_id in (
            getattr(
                step,
                "depends_on",
                [],
            )
            or []
        ):
            dependency = steps.get(dependency_id)

            if dependency is not None:
                result[dependency_id] = dependency

        return result

    def build_agent_context(
        self,
        plan: Any,
        step: Any,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Construye la vista de contexto que recibe un Agent.

        Esta vista no representa necesariamente todos los providers
        disponibles. Solo expone la información relevante para
        la ejecución del Agent.

        architecture y project_analysis son claves de runtime.
        No representan ContextProviders.
        """

        agent_context = {
            "execution": {
                "plan_id": getattr(
                    plan,
                    "id",
                    None,
                ),
                "intent": getattr(
                    plan,
                    "intent",
                    None,
                ),
                "original_task": getattr(
                    plan,
                    "original_task",
                    None,
                ),
                "current_step": {
                    "id": getattr(
                        step,
                        "id",
                        None,
                    ),
                    "unit_type": getattr(
                        step,
                        "unit_type",
                        None,
                    ),
                    "unit_name": getattr(
                        step,
                        "unit_name",
                        None,
                    ),
                    "description": getattr(
                        step,
                        "description",
                        None,
                    ),
                },
            }
        }

        dependencies = self.get_dependency_results(
            context,
            step,
        )

        if dependencies:
            agent_context["execution"]["dependencies"] = dependencies

        # Providers + materializaciones runtime.
        #
        # architecture:
        #   runtime / Engine / dependency materialization
        #
        # project_analysis:
        #   runtime / Engine / dependency materialization
        #
        # No son ContextProviders y por eso no aparecen
        # en ExecutionPlan.DEFAULT_CONTEXT_REQUIREMENTS.
        for key in (
            "project",
            "architecture",
            "project_analysis",
            "swarmforge",
            "gentleman",
            "standards",
            "engram",
            "memory",
            "obsidian",
            "documents",
            "spec",
        ):
            if key in context and context[key]:
                agent_context[key] = context[key]

        return agent_context

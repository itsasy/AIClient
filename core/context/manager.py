from __future__ import annotations

import logging
from copy import deepcopy
from typing import Any

from core.context.base import BaseContextProvider
from core.context.registry import ContextRegistry
from core.context.documents_provider import DocumentsProvider
from core.context.engram_provider import EngramProvider
from core.context.gentleman_provider import GentlemanProvider
from core.context.memory_provider import MemoryProvider
from core.context.obsidian_provider import ObsidianProvider
from core.context.project_provider import ProjectProvider
from core.context.spec_provider import SpecProvider
from core.context.standards_provider import StandardsProvider
from core.context.swarmforge_provider import SwarmForgeProvider

logger = logging.getLogger(__name__)


class ContextManager:
    """
    Construye y controla el contexto de ejecución.

    El ContextManager:

        - Resuelve providers mediante ContextRegistry.
        - Carga contexto bajo demanda.
        - Mantiene el contexto de runtime.
        - Construye vistas específicas para Agents.

    No:

        - Decide la intención.
        - Construye ExecutionPlans.
        - Ejecuta Agents.
        - Ejecuta Skills.
        - Construye prompts LLM.
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

        context: dict[str, Any] = deepcopy(existing_context or {})

        execution = context.setdefault(
            "execution",
            {},
        )

        execution.update(
            {
                "plan_id": getattr(plan, "id", None),
                "intent": getattr(plan, "intent", None),
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
                "id": getattr(step, "id", None),
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

        requirements = getattr(
            plan,
            "context_requirements",
            {},
        )

        for key, required in requirements.items():

            if not required:
                continue

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

        for key in (
            "project",
            "architecture",
            "project_analysis",
            "swarmforge",
            "gentleman",
            "standards",
            "engram",
            "obsidian",
            "documents",
            "spec",
        ):

            if key in context:
                agent_context[key] = context[key]

        return agent_context

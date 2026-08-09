from __future__ import annotations

import logging
from copy import deepcopy
from typing import Any

from core.context.engram_provider import EngramProvider
from core.context.gentleman_provider import GentlemanProvider
from core.context.memory_provider import MemoryProvider
from core.context.obsidian_provider import ObsidianProvider
from core.context.project_provider import ProjectProvider
from core.context.standards_provider import StandardsProvider
from core.context.documents_provider import DocumentsProvider
from core.context.spec_provider import SpecProvider
from core.context.swarmforge_provider import SwarmForgeProvider

logger = logging.getLogger(__name__)


class ContextManager:
    """
    Construye y controla el contexto de ejecución.

    Principio fundamental:
        runtime context != LLM context

    El contexto interno puede contener información amplia.
    Cada Agent recibe únicamente la vista necesaria para su tarea.

    Los proveedores solo se cargan si el plan los solicita
    mediante context_requirements.
    """

    def __init__(
        self,
        providers: dict[str, Any] | None = None,
    ) -> None:
        # Proveedores por defecto
        self._providers = {
            "project": ProjectProvider(),
            "engram": EngramProvider(),
            "memory": MemoryProvider(),
            "obsidian": ObsidianProvider(),
            "gentleman": GentlemanProvider(),
            "standards": StandardsProvider(),
            "documents": DocumentsProvider(),
            "spec": SpecProvider(),
            "swarmforge": SwarmForgeProvider(),
        }

        # Sobrescribir con providers personalizados si se pasan
        if providers:
            self._providers.update(providers)

    # ==========================================================
    # Base context
    # ==========================================================

    def build(
        self,
        plan: Any,
        step: Any | None = None,
        existing_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Construye contexto base sin destruir el contexto existente.
        """
        context: dict[str, Any] = deepcopy(existing_context or {})

        context.setdefault("execution", {})
        context["execution"].update(
            {
                "plan_id": getattr(plan, "id", None),
                "intent": getattr(plan, "intent", None),
                "original_task": getattr(plan, "original_task", None),
                "execution_mode": getattr(plan, "execution_mode", None),
            }
        )

        if step is not None:
            context["execution"]["current_step"] = {
                "id": getattr(step, "id", None),
                "unit_type": getattr(step, "unit_type", None),
                "unit_name": getattr(step, "unit_name", None),
                "description": getattr(step, "description", None),
                "params": dict(getattr(step, "params", {}) or {}),
                "depends_on": list(getattr(step, "depends_on", []) or []),
            }

        # ======================================================
        # Cargar proveedores bajo demanda según el plan
        # ======================================================
        if plan is not None:
            for key, provider in self._providers.items():
                if plan.requires_context(key):
                    try:
                        provider.load(plan, context)
                        logger.debug("Contexto cargado: %s", key)
                    except Exception as e:
                        logger.warning("Error cargando proveedor %s: %s", key, e)

        return context

    # ==========================================================
    # Step results
    # ==========================================================

    def record_step_result(
        self,
        context: dict[str, Any],
        step: Any,
        result: Any,
    ) -> None:
        """
        Registra el resultado de un step en el contexto de runtime.
        """
        execution = context.setdefault("execution", {})
        steps = execution.setdefault("steps", {})
        step_id = getattr(step, "id", None)

        if not step_id:
            return

        steps[step_id] = {
            "id": step_id,
            "unit_type": getattr(step, "unit_type", None),
            "unit_name": getattr(step, "unit_name", None),
            "description": getattr(step, "description", None),
            "result": result,
        }

    # ==========================================================
    # Dependency context
    # ==========================================================

    def get_dependency_results(
        self,
        context: dict[str, Any],
        step: Any,
    ) -> dict[str, Any]:
        """
        Obtiene los resultados de los steps de los que depende el actual.
        """
        execution = context.get("execution", {})
        steps = execution.get("steps", {})
        dependencies = getattr(step, "depends_on", []) or []

        result: dict[str, Any] = {}
        for dependency_id in dependencies:
            dependency = steps.get(dependency_id)
            if dependency is not None:
                result[dependency_id] = dependency

        return result

    # ==========================================================
    # Agent context
    # ==========================================================

    def build_agent_context(
        self,
        plan: Any,
        step: Any,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Construye el contexto específico que recibirá un Agent.
        """
        agent_context: dict[str, Any] = {
            "execution": {
                "plan_id": getattr(plan, "id", None),
                "intent": getattr(plan, "intent", None),
                "original_task": getattr(plan, "original_task", None),
                "current_step": {
                    "id": getattr(step, "id", None),
                    "unit_type": getattr(step, "unit_type", None),
                    "unit_name": getattr(step, "unit_name", None),
                    "description": getattr(step, "description", None),
                },
            }
        }

        dependency_results = self.get_dependency_results(context, step)
        if dependency_results:
            agent_context["execution"]["dependencies"] = dependency_results

        # Copiar contexto relevante para el agente
        for key in (
            "project",
            "architecture",
            "project_analysis",
            "swarmforge",
            "gentleman",
            "standards",
        ):
            if key in context:
                agent_context[key] = context[key]

        return agent_context

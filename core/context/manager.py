from __future__ import annotations

import logging
from copy import deepcopy
from typing import Any

logger = logging.getLogger(__name__)


class ContextManager:
    """
    Construye y controla el contexto de ejecución.

    Principio fundamental:

        runtime context != LLM context

    El contexto interno puede contener información amplia.
    Cada Agent recibe únicamente la vista necesaria para su tarea.
    """

    def __init__(
        self,
        providers: dict[str, Any] | None = None,
    ) -> None:

        self.providers = dict(
            providers or {},
        )

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

        context: dict[str, Any] = deepcopy(
            existing_context or {},
        )

        context.setdefault(
            "execution",
            {},
        )

        context["execution"].update(
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
            context["execution"]["current_step"] = {
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

        return context

    # ==========================================================
    # Provider context
    # ==========================================================

    def load_providers(
        self,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Ejecuta proveedores de contexto registrados.

        Cada proveedor puede devolver:

            dict

        o:

            None

        Los datos se almacenan bajo la clave del proveedor.
        """

        for name, provider in self.providers.items():
            try:
                if hasattr(provider, "build"):
                    data = provider.build(
                        context,
                    )
                elif hasattr(provider, "get_context"):
                    data = provider.get_context(
                        context,
                    )
                elif callable(provider):
                    data = provider(
                        context,
                    )
                else:
                    logger.warning(
                        "Provider '%s' no tiene interfaz válida",
                        name,
                    )
                    continue

                if data is None:
                    continue

                if not isinstance(data, dict):
                    logger.warning(
                        "Provider '%s' devolvió %s; " "se esperaba dict",
                        name,
                        type(data).__name__,
                    )
                    continue

                context[name] = data

            except Exception:
                logger.exception(
                    "Error cargando provider=%s",
                    name,
                )

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

        Los resultados se conservan por ID para permitir que
        steps dependientes los consulten.
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
        Obtiene exclusivamente los resultados de los steps
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

        dependencies = (
            getattr(
                step,
                "depends_on",
                [],
            )
            or []
        )

        result: dict[str, Any] = {}

        for dependency_id in dependencies:
            dependency = steps.get(
                dependency_id,
            )

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

        No copia todo el runtime context.

        Actualmente soporta especialmente:

            agent:architect
        """

        agent_context: dict[str, Any] = {
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
            },
        }

        dependency_results = self.get_dependency_results(
            context,
            step,
        )

        if dependency_results:
            agent_context["execution"]["dependencies"] = dependency_results

        unit_name = (
            str(
                getattr(
                    step,
                    "unit_name",
                    "",
                )
            )
            .strip()
            .lower()
        )

        # ------------------------------------------------------
        # Arquitectura
        # ------------------------------------------------------

        if unit_name == "architect":
            self._add_architecture_context(
                agent_context,
                dependency_results,
            )

        return agent_context

    # ==========================================================
    # Architecture context
    # ==========================================================

    def _add_architecture_context(
        self,
        target: dict[str, Any],
        dependencies: dict[str, Any],
    ) -> None:

        for dependency in dependencies.values():

            result = dependency.get(
                "result",
            )

            if not isinstance(
                result,
                dict,
            ):
                continue

            # ExecutionResult / dispatcher wrappers.
            nested = result.get(
                "result",
            )

            if isinstance(
                nested,
                dict,
            ):
                result = nested

            architecture_context = result.get(
                "architecture_context",
            )

            if isinstance(
                architecture_context,
                dict,
            ):
                target["architecture"] = architecture_context

                target["project_summary"] = result.get(
                    "summary",
                    "",
                )

                return

            # Compatibilidad con resultados antiguos.
            snapshot = result.get(
                "snapshot",
            )

            if isinstance(
                snapshot,
                dict,
            ):
                target["architecture"] = self._compact_snapshot(
                    snapshot,
                )

                target["project_summary"] = result.get(
                    "summary",
                    "",
                )

                return

    # ==========================================================
    # Compatibility
    # ==========================================================

    @staticmethod
    def _compact_snapshot(
        snapshot: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Convierte un snapshot antiguo en contexto arquitectónico
        sin transportar contenido fuente.
        """

        files = []

        for item in snapshot.get(
            "files",
            [],
        ):
            if not isinstance(
                item,
                dict,
            ):
                continue

            files.append(
                {
                    key: item.get(key)
                    for key in (
                        "path",
                        "filename",
                        "extension",
                        "language",
                        "lines",
                        "size",
                    )
                    if key in item
                }
            )

        return {
            "project": {
                "name": snapshot.get(
                    "project_name",
                    "Unknown",
                ),
                "root_path": snapshot.get(
                    "root_path",
                    "",
                ),
                "file_count": len(files),
                "directory_count": len(
                    snapshot.get(
                        "directories",
                        [],
                    )
                ),
            },
            "languages": dict(
                snapshot.get(
                    "languages",
                    {},
                )
            ),
            "extensions": dict(
                snapshot.get(
                    "extensions",
                    {},
                )
            ),
            "directories": snapshot.get(
                "directories",
                [],
            ),
            "files": files,
        }

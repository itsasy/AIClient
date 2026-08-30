from __future__ import annotations

from typing import Any

from core.context.base import BaseContextProvider
from core.execution_plan import ExecutionPlan
from core.project_inspector import ProjectInspector


class ProjectProvider(BaseContextProvider):
    """
    Inspección estructural del proyecto objetivo.

    Por defecto usa TARGET_PROJECT_ROOT (producto).
    No ejecuta DiscoveryEngine, TransformationPlanner ni SkillRegistry P8.
    """

    key = "project"
    name = "Project Context"
    description = "Inspección estructural del proyecto objetivo."

    def __init__(self) -> None:
        self.inspector = ProjectInspector()

    def load(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if context:
            execution = context.get("execution") or {}
            current = execution.get("current_step") or {}
            params = dict(current.get("params") or {})

        path = params.get("path")
        prefer_target = self._resolve_prefer_target(plan, params)

        snapshot = self.inspector.inspect_snapshot(
            path=path,
            prefer_target=prefer_target,
        )

        architecture_context = snapshot.to_architecture_context(
            max_files=80,
            max_directories=60,
            include_file_content=False,
        )

        return {
            "summary": snapshot.summary(),
            "root_path": snapshot.root_path,
            "file_count": snapshot.file_count,
            "directory_count": getattr(snapshot, "directory_count", 0),
            "architecture_context": architecture_context,
            "prefer_target": prefer_target,
        }

    @staticmethod
    def _resolve_prefer_target(
        plan: ExecutionPlan,
        params: dict[str, Any],
    ) -> bool:
        if "prefer_target" in params:
            return bool(params.get("prefer_target"))
        if "target" in params:
            return bool(params.get("target"))

        task = (
            str(getattr(plan, "original_task", None) or "")
            + " "
            + str(getattr(plan, "objective", None) or "")
        ).lower()

        if any(
            token in task
            for token in (
                "aiclient",
                "orquestador",
                "analiza aiclient",
                "analizar aiclient",
            )
        ):
            return False

        return True
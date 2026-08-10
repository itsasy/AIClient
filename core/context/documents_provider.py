from typing import Any

from core.context.base import BaseContextProvider
from core.execution_plan import ExecutionPlan
from core.project_inspector import ProjectInspector


class ProjectProvider(BaseContextProvider):

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

        snapshot = self.inspector.inspect_snapshot()

        return {
            "snapshot": snapshot,
            "architecture": snapshot.to_architecture_context(),
        }

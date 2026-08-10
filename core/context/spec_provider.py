from typing import Any

from core.context.base import BaseContextProvider
from core.execution_plan import ExecutionPlan
from core.spec_manager import SpecManager


class SpecProvider(BaseContextProvider):

    key = "spec"

    def __init__(self) -> None:
        self.specs = SpecManager()

    def load(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
    ) -> dict[str, Any]:

        spec_name = plan.params.get("spec_name")

        if not spec_name:
            return {}

        spec = self.specs.load_spec_by_name(spec_name)

        if not spec:
            return {}

        return {
            "spec": spec,
        }

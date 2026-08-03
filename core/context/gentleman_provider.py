from core.execution_plan import ExecutionPlan
from core.gentleman_skills import GentlemanSkills
from core.context.base import BaseContextProvider


class GentlemanProvider(BaseContextProvider):

    key = "gentleman"

    def __init__(self):

        self.skills = GentlemanSkills()

    def load(
        self,
        plan: ExecutionPlan,
        context: dict,
    ) -> None:

        relevant = self.skills.find_relevant(
            plan.original_task,
        )

        if not relevant:
            return

        context[self.key] = {name: self.skills.get_skill(name) for name in relevant}

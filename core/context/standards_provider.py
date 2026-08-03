from core.execution_plan import ExecutionPlan
from core.learner import ContinuousLearner
from core.context.base import BaseContextProvider


class StandardsProvider(BaseContextProvider):

    key = "standards"

    def __init__(self):

        self.learner = ContinuousLearner()

    def load(
        self,
        plan: ExecutionPlan,
        context: dict,
    ) -> None:

        standards = self.learner.get_context()

        if not standards:
            return

        context[self.key] = standards

from core.execution_plan import ExecutionPlan
from core.standards_learner import StandardsLearner
from core.context.base import BaseContextProvider


class StandardsProvider(BaseContextProvider):
    """
    Proveedor de estándares aprendidos del proyecto.

    Responsabilidad:
    - Exponer estándares persistidos.
    - No ejecutar aprendizaje.
    - No inicializar LLM.
    """

    key = "standards"

    def __init__(self):

        self.standards = StandardsLearner()

    def load(
        self,
        plan: ExecutionPlan,
        context: dict,
    ) -> None:

        standards = self.standards.list_standards()

        if not standards:
            return

        context[self.key] = {
            "learned_standards": standards,
        }

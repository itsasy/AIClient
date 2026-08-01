from core.spec_manager import SpecManager
from core.context.provider import ContextProvider


class SpecProvider(ContextProvider):

    def __init__(self):

        self.specs = SpecManager()

    def load(
        self,
        plan,
        context,
    ):

        if not plan.spec_name:
            return

        spec = self.specs.load_spec_by_name(plan.spec_name)

        if spec:

            context["spec"] = spec

from core.spec_manager import SpecManager
from core.context.base import BaseContextProvider


class SpecProvider(BaseContextProvider):

    key = "spec"

    def __init__(self):

        self.specs = SpecManager()

    def load(
        self,
        plan,
        context,
    ) -> None:

        if not plan.spec_name:
            return

        spec = self.specs.load_spec_by_name(
            plan.spec_name,
        )

        if not spec:
            return

        context[self.key] = spec

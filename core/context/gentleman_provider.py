import logging
from typing import Any

from core.context.base import BaseContextProvider
from core.execution_plan import ExecutionPlan
from core.gentleman_skills import GentlemanSkills

logger = logging.getLogger(__name__)


class GentlemanProvider(BaseContextProvider):

    key = "gentleman"

    def __init__(self) -> None:
        self.skills = GentlemanSkills()

    def load(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
    ) -> dict[str, Any]:

        relevant = self.skills.find_relevant(
            query=plan.original_task,
            limit=5,
        )

        if not relevant:
            return {}

        loaded = {}

        for name in relevant:
            content = self.skills.get_skill(name)

            if not content:
                continue

            loaded[name] = {
                "content": content,
                "metadata": self.skills.get_metadata(name) or {},
            }

        if not loaded:
            return {}

        logger.info(
            "Gentleman skills cargadas: %s",
            list(loaded.keys()),
        )

        return loaded

import logging

from agents.self_critic import SelfCriticAgent

from core.execution_plan import (
    ExecutionPlan,
    ExecutionStep,
)

from skills.manager import SkillManager

logger = logging.getLogger(__name__)


class Subagent:
    """
    Ejecuta un ExecutionStep.

    En el futuro podrá ejecutar:

    - Skills
    - Agentes
    - Workflows
    - Plugins
    - MCP Servers
    """

    def __init__(self):

        self.skills = SkillManager()
        self.critic = SelfCriticAgent()

    # ---------------------------------------------------------

    def execute(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict | None = None,
    ) -> dict:

        context = context or {}

        retries = 0
        max_retries = plan.max_retries

        while retries <= max_retries:

            try:

                logger.info(
                    "Ejecutando step: %s",
                    step.description,
                )

                step.status = "running"

                result = self.skills.execute(
                    step.skill,
                    **step.params,
                )

                output = self._extract_output(result)

                if plan.requires_self_critic:

                    evaluation = self.critic.process(
                        plan=plan,
                        context=context,
                        draft_response=output,
                    )

                    score = evaluation.get(
                        "alignment_score",
                        10,
                    )

                    if score < 5:

                        retries += 1

                        logger.warning(
                            "Self-Critic rechazó el step (%s/%s)",
                            retries,
                            max_retries,
                        )

                        advice = evaluation.get(
                            "course_correction_advice",
                        )

                        if advice:

                            self._apply_correction(
                                step,
                                advice,
                            )

                        continue

                step.status = "completed"

                return {
                    "success": True,
                    "result": result,
                }

            except Exception as e:

                retries += 1

                logger.exception(
                    "Error ejecutando step.",
                )

                if retries > max_retries:

                    step.status = "failed"

                    return {
                        "success": False,
                        "error": str(e),
                    }

        step.status = "failed"

        return {
            "success": False,
            "error": "Max retries alcanzado.",
        }

    # ---------------------------------------------------------

    @staticmethod
    def _apply_correction(
        step: ExecutionStep,
        advice: str,
    ):

        for field in (
            "task",
            "prompt",
            "content",
        ):

            if field in step.params:

                step.params[field] += "\n\n" "[SELF-CRITIC]\n" f"{advice}"

                return

    # ---------------------------------------------------------

    @staticmethod
    def _extract_output(
        result,
    ) -> str:

        if not isinstance(result, dict):
            return str(result)

        payload = result.get(
            "payload",
            {},
        )

        return payload.get("output") or payload.get("message") or str(result)

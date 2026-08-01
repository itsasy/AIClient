import logging

from core.execution_plan import ExecutionStep
from skills.manager import SkillManager
from agents.self_critic import SelfCriticAgent

logger = logging.getLogger(__name__)


class Subagent:
    """
    Ejecuta pasos individuales de un ExecutionPlan.

    Responsabilidades:
    - Ejecutar skills.
    - Validar resultado.
    - Aplicar retry.
    """

    def __init__(self):
        self.skill_manager = SkillManager()
        self.critic = SelfCriticAgent()

    def execute_step(
        self,
        step: ExecutionStep,
        context: dict | None = None,
        max_retries: int = 2,
    ) -> dict:

        retries = 0

        while retries <= max_retries:

            try:

                logger.info(
                    "Ejecutando step: %s",
                    step.description,
                )

                result = self.skill_manager.execute(
                    step.skill,
                    **step.params,
                )

                output = self._extract_output(result)

                evaluation = self.critic.process(
                    task=step.description,
                    context=context or {},
                    draft_response=output,
                )

                score = evaluation.get(
                    "alignment_score",
                    0,
                )

                if score >= 5:

                    step.status = "completed"

                    return {
                        "success": True,
                        "result": result,
                        "evaluation": evaluation,
                    }

                logger.warning(
                    "Step rechazado score=%s",
                    score,
                )

                retries += 1

            except Exception as e:

                logger.exception(
                    "Error ejecutando step %s",
                    step.description,
                )

                retries += 1

                if retries > max_retries:
                    step.status = "failed"

                    return {
                        "success": False,
                        "error": str(e),
                    }

        return {
            "success": False,
            "error": "Max retries exceeded",
        }

    def _extract_output(
        self,
        result: dict,
    ) -> str:

        if not isinstance(result, dict):
            return str(result)

        payload = result.get(
            "payload",
            {},
        )

        return payload.get("output") or payload.get("message") or str(result)

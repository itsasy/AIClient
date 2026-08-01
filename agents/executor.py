import logging

from agents.base import Agent
from core.execution_plan import ExecutionPlan
from skills.manager import SkillManager

logger = logging.getLogger(__name__)


class ExecutorAgent(Agent):

    name = "executor"

    role = "Ejecutor autónomo de tareas"

    def __init__(self):
        self.skill_manager = SkillManager()

    def process(
        self,
        plan: ExecutionPlan,
        context: dict | None = None,
    ) -> str:

        if plan.steps:

            return self._execute_steps(
                plan,
                context or {},
            )

        if plan.skill:

            return self._execute_skill(
                plan.skill,
                plan.params,
            )

        return "⚠️ ExecutionPlan recibido sin " "skill ni pasos ejecutables."

    def _execute_steps(
        self,
        plan: ExecutionPlan,
        context: dict,
    ) -> str:

        results = []

        for index, step in enumerate(plan.steps, start=1):

            logger.info(
                "Ejecutando paso %s: %s",
                index,
                step.description,
            )

            try:

                result = self.skill_manager.execute(
                    step.skill,
                    **step.params,
                )

                step.status = "completed"

                results.append(
                    self._format_result(
                        index,
                        step.description,
                        result,
                    )
                )

            except Exception as e:

                logger.exception(
                    "Error ejecutando paso %s",
                    step.description,
                )

                step.status = "failed"

                results.append(f"❌ Paso {index} falló: {e}")

        return "\n\n".join(results)

    def _execute_skill(
        self,
        skill_name: str,
        params: dict,
    ) -> str:

        try:

            result = self.skill_manager.execute(
                skill_name,
                **params,
            )

            return self._format_result(
                1,
                skill_name,
                result,
            )

        except Exception as e:

            logger.exception(
                "Error ejecutando skill %s",
                skill_name,
            )

            return f"❌ Error ejecutando " f"{skill_name}: {e}"

    def _format_result(
        self,
        index: int,
        description: str,
        result: dict,
    ) -> str:

        if not isinstance(result, dict):

            return f"✅ Paso {index}: " f"{description}\n" f"{result}"

        payload = result.get(
            "payload",
            {},
        )

        message = payload.get("message") or payload.get("output") or str(payload)

        return f"✅ Paso {index}: " f"{description}\n\n" f"{message}"

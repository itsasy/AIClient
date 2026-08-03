import logging

from agents.base import Agent
from core.subagent import Subagent

from core.execution_plan import (
    ExecutionPlan,
    ExecutionStep,
)

logger = logging.getLogger(__name__)


class ExecutorAgent(Agent):

    name = "executor"

    role = "Execution Engine"

    def __init__(self):

        self.subagent = Subagent()

    # ---------------------------------------------------------

    def process(
        self,
        plan: ExecutionPlan,
        context: dict | None = None,
    ) -> str:

        context = context or {}

        if not plan.steps:

            return self._execute_single(
                plan,
                context,
            )

        return self._execute_plan(
            plan,
            context,
        )

    # ---------------------------------------------------------

    def _execute_plan(
        self,
        plan: ExecutionPlan,
        context: dict,
    ) -> str:

        outputs = []

        completed = 0

        failed = 0

        logger.info(
            "Ejecutando plan (%s pasos)",
            len(plan.steps),
        )

        for index, step in enumerate(
            plan.steps,
            start=1,
        ):

            logger.info(
                "Step %s/%s -> %s",
                index,
                len(plan.steps),
                step.description,
            )

            result = self.subagent.execute(
                plan=plan,
                step=step,
                context=context,
            )

            if result["success"]:

                completed += 1

                outputs.append(
                    self._format_success(
                        index,
                        step,
                        result,
                    )
                )

                continue

            failed += 1

            outputs.append(
                self._format_failure(
                    index,
                    step,
                    result,
                )
            )

            if plan.stop_on_error:

                logger.warning("Plan detenido por fallo.")

                break

        outputs.append("")

        outputs.append(f"Resumen: {completed} completados | {failed} fallidos")

        return "\n".join(outputs)

    # ---------------------------------------------------------

    def _execute_single(
        self,
        plan: ExecutionPlan,
        context: dict,
    ) -> str:

        if not plan.skill:

            return "No existe ninguna Skill para ejecutar."

        step = ExecutionStep(
            description=plan.objective or plan.original_task,
            skill=plan.skill,
            params=plan.params,
        )

        result = self.subagent.execute(
            plan=plan,
            step=step,
            context=context,
        )

        if result["success"]:

            return self._format_success(
                1,
                step,
                result,
            )

        return self._format_failure(
            1,
            step,
            result,
        )

    # ---------------------------------------------------------

    @staticmethod
    def _format_success(
        index: int,
        step: ExecutionStep,
        result: dict,
    ) -> str:

        payload = result["result"].get(
            "payload",
            {},
        )

        output = payload.get("message") or payload.get("output") or str(payload)

        return f"✅ Paso {index}\n" f"{step.description}\n\n" f"{output}"

    # ---------------------------------------------------------

    @staticmethod
    def _format_failure(
        index: int,
        step: ExecutionStep,
        result: dict,
    ) -> str:

        return f"❌ Paso {index}\n" f"{step.description}\n\n" f"{result.get('error')}"

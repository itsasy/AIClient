from __future__ import annotations

import logging

from agents.base import Agent

from core.execution_plan import (
    ExecutionPlan,
    ExecutionStep,
)

from runtime.skill_runtime import SkillRuntime

logger = logging.getLogger(__name__)


class ExecutorAgent(Agent):

    name = "executor"

    role = "Execution Engine"

    def __init__(self):

        self.skill_runtime = SkillRuntime()

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

    def _execute_plan(
        self,
        plan: ExecutionPlan,
        context: dict,
    ) -> str:

        outputs = []

        completed = 0

        failed = 0

        logger.info(
            "Ejecutando plan pasos=%s",
            len(plan.steps),
        )

        for index, step in enumerate(
            plan.steps,
            start=1,
        ):

            result = self.skill_runtime.execute(
                plan,
                step,
                context,
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

            else:

                failed += 1

                outputs.append(
                    self._format_failure(
                        index,
                        step,
                        result,
                    )
                )

                if plan.stop_on_error:

                    break

        outputs.append("")

        outputs.append(f"Resumen: {completed} completados | {failed} fallidos")

        return "\n".join(outputs)

    def _execute_single(
        self,
        plan: ExecutionPlan,
        context: dict,
    ) -> str:

        step = ExecutionStep(
            description=(plan.objective or plan.original_task),
            skill=plan.skill,
            params=plan.params,
        )

        result = self.skill_runtime.execute(
            plan,
            step,
            context,
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

    @staticmethod
    def _format_success(
        index: int,
        step: ExecutionStep,
        result: dict,
    ) -> str:

        payload = result.get(
            "result",
            {},
        ).get(
            "payload",
            {},
        )

        output = payload.get("message") or payload.get("output") or str(payload)

        return f"✅ Paso {index}\n" f"{step.description}\n\n" f"{output}"

    @staticmethod
    def _format_failure(
        index: int,
        step: ExecutionStep,
        result: dict,
    ) -> str:

        return f"❌ Paso {index}\n" f"{step.description}\n\n" f"{result.get('error')}"

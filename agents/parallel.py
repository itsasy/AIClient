from __future__ import annotations

import asyncio
import copy

from typing import Any

from core.execution_plan import ExecutionPlan

from runtime.execution_runtime import ExecutionRuntime


class ParallelAgentSystem:
    """
    Ejecuta múltiples agentes en paralelo.
    """

    def __init__(
        self,
        runtime: ExecutionRuntime | None = None,
    ):

        self.runtime = runtime or ExecutionRuntime()

    async def run(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any] | None = None,
    ) -> str:

        context = dict(context or {})

        architect_plan = self._clone_plan(
            plan,
        )

        architect_plan.execution_unit_type = "agent"

        architect_plan.execution_unit = "architect"

        coder_plan = self._clone_plan(
            plan,
        )

        coder_plan.execution_unit_type = "agent"

        coder_plan.execution_unit = "coder"

        architect_task = asyncio.to_thread(
            self.runtime.execute,
            architect_plan,
            context.copy(),
        )

        coder_task = asyncio.to_thread(
            self.runtime.execute,
            coder_plan,
            context.copy(),
        )

        architect_result, coder_result = await asyncio.gather(
            architect_task,
            coder_task,
        )

        return (
            "**Arquitecto:**\n"
            f"{architect_result.output}\n\n"
            "**Programador:**\n"
            f"{coder_result.output}"
        )

    # ==========================================================
    # Helpers
    # ==========================================================

    def _clone_plan(
        self,
        plan: ExecutionPlan,
    ) -> ExecutionPlan:

        return copy.deepcopy(
            plan,
        )

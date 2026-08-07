from __future__ import annotations

import logging
import time
from typing import Any

from core.execution_plan import ExecutionPlan
from core.execution_result import ExecutionResult
from core.execution_step import ExecutionStep
from core.context.manager import ContextManager
from core.intent import IntentAnalyzer, IntentResult
from core.planning import PlanBuilder

from runtime.dispatcher import UnitDispatcher
from runtime.registry.agent_registry import AgentRegistry
from runtime.registry.skill_registry import SkillRegistry

logger = logging.getLogger(__name__)


class ExecutionEngine:
    """
    Único dueño del lifecycle de ejecución.

    Coordina las etapas, no las implementa.

    Flujo:
        User input → IntentAnalyzer → PlanBuilder → ExecutionPlan
        → validate → context → execute → finalize → ExecutionResult
    """

    name = "execution_engine"

    def __init__(
        self,
        agent_registry: AgentRegistry | None = None,
        skill_registry: SkillRegistry | None = None,
        context_manager: ContextManager | None = None,
        intent_analyzer: IntentAnalyzer | None = None,
        plan_builder: PlanBuilder | None = None,
    ):
        self.agent_registry = agent_registry or AgentRegistry()
        self.skill_registry = skill_registry or SkillRegistry()
        self.context_manager = context_manager or ContextManager()
        self.intent_analyzer = intent_analyzer or IntentAnalyzer()
        self.plan_builder = plan_builder or PlanBuilder()

        self.dispatcher = UnitDispatcher(
            agent_registry=self.agent_registry,
            skill_registry=self.skill_registry,
        )

        self.metrics = {
            "executions": 0,
            "success": 0,
            "partial": 0,
            "failed": 0,
            "cancelled": 0,
        }

    # ==========================================================
    # Public API
    # ==========================================================

    def execute_from_input(
        self,
        user_input: str,
        metadata: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        logger.info("Engine: procesando entrada: %s", user_input[:100])

        intent = self.intent_analyzer.analyze(user_input)
        plan = self.plan_builder.build(intent=intent, original_task=user_input)

        if metadata:
            plan.metadata.update(metadata)

        return self.execute(plan)

    def execute(self, plan: ExecutionPlan) -> ExecutionResult:
        started = time.monotonic()
        self.metrics["executions"] += 1

        try:
            errors = plan.validate()
            if errors:
                return self._fail(plan, "; ".join(errors))

            plan.mark_validated()
            plan.mark_running()

            context = self.context_manager.build(plan) or {}
            plan.loaded_context = context

            if plan.is_multi_step():
                result = self._execute_steps(plan, context)
            else:
                result = self._execute_single(plan, context)

            duration = round(time.monotonic() - started, 3)
            result.metadata.update(
                {
                    "engine": self.name,
                    "duration": duration,
                    "plan_id": plan.id,
                }
            )

            self._apply_plan_state(plan, result)
            self._update_metrics(result)
            return result

        except Exception as exc:
            logger.exception("Engine error")
            try:
                plan.mark_failed()
            except Exception:
                pass
            return self._fail(plan, str(exc))

    # ==========================================================
    # Ejecución interna (coordinación)
    # ==========================================================

    def _execute_single(self, plan: ExecutionPlan, context: dict) -> ExecutionResult:
        if not plan.execution_unit_type or not plan.execution_unit:
            return self._fail(plan, "Plan sin unidad de ejecución.")

        step = ExecutionStep(
            description=plan.objective or plan.original_task,
            unit_type=plan.execution_unit_type,
            unit_name=plan.execution_unit,
            params=plan.params,
        )
        return self.dispatcher.dispatch(plan, step, context)

    def _execute_steps(self, plan: ExecutionPlan, context: dict) -> ExecutionResult:
        if not plan.steps:
            return self._fail(plan, "Plan multi_step sin pasos.")

        ordered = self._resolve_order(plan.steps)
        results: list[ExecutionResult] = []
        failed_steps: list[str] = []

        for step in ordered:
            result = self.dispatcher.dispatch(plan, step, context)
            results.append(result)

            if result.is_failure:
                failed_steps.append(step.id)
                if plan.stop_on_error:
                    break

        if not failed_steps:
            return ExecutionResult.success(
                plan_id=plan.id,
                result=[r.result for r in results],
                executor=self.name,
            )
        elif not results:
            return self._fail(plan, "Todos los steps fallaron.")
        else:
            return ExecutionResult.partial(
                plan_id=plan.id,
                result=[r.result for r in results],
                error=f"Fallaron {len(failed_steps)} pasos",
                executor=self.name,
            )

    # ==========================================================
    # Helpers
    # ==========================================================

    def _resolve_order(self, steps: list[ExecutionStep]) -> list[ExecutionStep]:
        ordered: list[ExecutionStep] = []
        resolved: set[str] = set()
        pending = list(steps)
        available_ids = {step.id for step in steps}

        while pending:
            progress = False
            for step in pending[:]:
                missing = [dep for dep in step.depends_on if dep not in available_ids]
                if missing:
                    raise ValueError(f"Dependencias inexistentes: {missing}")
                if all(dep in resolved for dep in step.depends_on):
                    ordered.append(step)
                    resolved.add(step.id)
                    pending.remove(step)
                    progress = True
            if not progress:
                raise RuntimeError("Dependencias circulares en el plan.")
        return ordered

    def _apply_plan_state(self, plan: ExecutionPlan, result: ExecutionResult) -> None:
        if result.is_success:
            plan.mark_completed()
        elif result.is_partial:
            plan.mark_partial()
        elif result.is_failure:
            plan.mark_failed()
        elif result.is_cancelled:
            plan.mark_cancelled()

    def _update_metrics(self, result: ExecutionResult) -> None:
        if result.is_success:
            self.metrics["success"] += 1
        elif result.is_partial:
            self.metrics["partial"] += 1
        elif result.is_failure:
            self.metrics["failed"] += 1
        elif result.is_cancelled:
            self.metrics["cancelled"] += 1

    def _fail(self, plan: ExecutionPlan, error: str) -> ExecutionResult:
        return ExecutionResult.fail(
            plan_id=plan.id,
            error=error,
            executor=self.name,
        )

    def get_metrics(self) -> dict[str, Any]:
        return self.metrics.copy()

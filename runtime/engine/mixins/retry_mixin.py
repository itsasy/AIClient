from __future__ import annotations
import logging
import time
from datetime import datetime
from typing import Any

from core.evaluation_result import EvaluationResult
from core.execution_plan import ExecutionPlan
from core.execution_result import ExecutionResult

logger = logging.getLogger(__name__)

class EngineRetryMixin:
    def _execute_with_retries(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
        started_at: datetime,
    ) -> ExecutionResult:
        max_retries = max(0, plan.get_max_retries())
        retries = 0

        try:
            while True:
                logger.info(
                    "Execution intento | plan=%s | retry=%s/%s",
                    plan.id,
                    retries,
                    max_retries,
                )

                # -------------------------------------------------
                # Execute
                # -------------------------------------------------
                if plan.is_multi_step():
                    result = self._execute_steps(plan, context)
                else:
                    result = self._execute_single(plan, context)

                if not isinstance(result, ExecutionResult):
                    raise TypeError("La ejecución debe devolver ExecutionResult.")

                # -------------------------------------------------
                # Evaluate (SelfCritic)
                # -------------------------------------------------
                result = self._evaluate(plan, result, context)

                if not isinstance(result, ExecutionResult):
                    raise TypeError("SelfCritic debe devolver ExecutionResult.")

                result.retries = retries
                result.started_at = started_at

                # -------------------------------------------------
                # Terminal exitoso / parcial / cancelado
                # -------------------------------------------------
                if result.is_success or result.is_partial or result.is_cancelled:
                    return result

                # -------------------------------------------------
                # Reconstruir EvaluationResult desde metadata (si existe)
                # -------------------------------------------------
                evaluation: EvaluationResult | None = None
                raw_eval = (result.metadata or {}).get("evaluation")

                if isinstance(raw_eval, dict):
                    try:
                        evaluation = EvaluationResult(
                            status=raw_eval.get("status", "unavailable"),
                            passed=raw_eval.get("passed"),
                            score=raw_eval.get("score"),
                            issues=list(raw_eval.get("issues") or []),
                            corrections=list(raw_eval.get("corrections") or []),
                            reason=raw_eval.get("reason"),
                            metadata=dict(raw_eval.get("metadata") or {}),
                        )
                    except Exception:
                        evaluation = None

                # -------------------------------------------------
                # Decisión de retry (única autoridad: RetryPolicy)
                # -------------------------------------------------
                decision = self.retry_policy.decide(
                    plan=plan,
                    execution_result=result,
                    evaluation=evaluation,
                    current_retries=retries,
                    max_retries=max_retries,
                )

                result.metadata["retry_decision"] = decision.to_dict()

                if not decision.should_retry or retries >= max_retries:
                    if result.is_retry or result.is_failure:
                        return ExecutionResult.fail(
                            plan_id=plan.id,
                            error=result.error or decision.reason,
                            executor=result.executor or self.name,
                            retries=retries,
                            metadata={
                                **dict(result.metadata or {}),
                                "retry_decision": decision.to_dict(),
                                "retry_exhausted": True,
                            },
                            started_at=started_at,
                        )
                    return result
                # -------------------------------------------------
                # Hay que reintentar
                # -------------------------------------------------
                retries += 1
                self.metrics["retries"] += 1

                result.retries = retries
                result.metadata.update(
                    {
                        "retry_count": retries,
                        "max_retries": max_retries,
                        "retry_decision": decision.to_dict(),
                    }
                )

                logger.info(
                    "RetryPolicy decidió reintentar | plan=%s | retry=%s/%s | reason=%s",
                    plan.id,
                    retries,
                    max_retries,
                    decision.reason,
                )

                self._reset_execution_context(plan, context)

                if decision.delay_seconds > 0:
                    time.sleep(decision.delay_seconds)

        finally:
            self._retry_context.pop(plan.id, None)

    def _reset_execution_context(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
    ) -> None:
        execution = context.setdefault("execution", {})
        if not isinstance(execution, dict):
            execution = {}
            context["execution"] = execution

        completed_steps = execution.get("steps")
        if not isinstance(completed_steps, dict):
            completed_steps = {}
            execution["steps"] = completed_steps

        for step in plan.steps:
            previous = completed_steps.get(step.id)

            if previous is None:
                step.reset()
                completed_steps.pop(step.id, None)
                continue

            if isinstance(previous, ExecutionResult):
                if previous.is_success:
                    continue
                step.reset()
                completed_steps.pop(step.id, None)
                continue

            if isinstance(previous, dict):
                if self._dependency_result_is_success(previous):
                    continue
                step.reset()
                completed_steps.pop(step.id, None)
                continue

            step.reset()
            completed_steps.pop(step.id, None)

        execution["steps"] = completed_steps


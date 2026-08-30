from __future__ import annotations
import json
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.analytics.metrics_store import MetricsStore
from core.analytics.models import ExecutionMetric
from core.context.manager import ContextManager
from core.engram_memory import EngramMemory
from core.evaluation_result import EvaluationResult
from core.retry_policy import RetryPolicy
from core.execution_plan import ExecutionPlan
from core.execution_result import ExecutionResult
from core.execution_step import ExecutionStep
from core.intent import IntentAnalyzer
from core.learner import ContinuousLearner
from core.planning import PlanBuilder
from core.self_critic import SelfCritic
from runtime.dispatcher import UnitDispatcher
from runtime.registry.agent_registry import AgentRegistry
from runtime.registry.skill_registry import SkillRegistry
from core.governance.capability_guard import CapabilityGuard

logger = logging.getLogger(__name__)

class EngineLifecycleMixin:
    def _finalize(
        self,
        plan: ExecutionPlan,
        result: ExecutionResult,
        started_monotonic: float,
        started_at: datetime,
    ) -> ExecutionResult:
        if not isinstance(result, ExecutionResult):
            result = ExecutionResult.fail(
                plan_id=plan.id,
                error="ExecutionEngine recibió un resultado inválido.",
                executor=self.name,
                started_at=started_at,
            )

        if result.plan_id != plan.id:
            result.plan_id = plan.id

        if result.is_retry:
            result = ExecutionResult.fail(
                plan_id=plan.id,
                error=result.error or "La ejecución terminó en retry inesperadamente.",
                executor=result.executor or self.name,
                retries=result.retries,
                metadata={
                    **dict(result.metadata or {}),
                    "invalid_terminal_retry": True,
                },
                started_at=started_at,
            )

        finished_at = datetime.now(timezone.utc)
        result.set_execution_window(started_at=started_at, finished_at=finished_at)

        self._apply_plan_state(plan, result)

        if result.is_success or result.is_partial:
            val_res = self._post_execution_check(plan)
            # Si val_res no es success, podríamos mutar el result,
            # pero por ahora lo mantenemos como advertencia en el plan
            if not val_res.is_success:
                result.error = (result.error or "") + " | Linter warning: " + str(val_res.error)

        duration = max(0.0, round(time.monotonic() - started_monotonic, 3))
        result.metadata.update(
            {
                "engine": self.name,
                "duration": duration,
                "plan_id": plan.id,
                "retries": result.retries,
                "terminal": result.is_terminal,
                "lint_error": plan.metadata.get("lint_error"),
            }
        )

        self._update_metrics(result)
        self._save_metric(plan, result, duration)
        self._retry_context.pop(plan.id, None)

        return result

    def _save_metric(
        self,
        plan: ExecutionPlan,
        result: ExecutionResult,
        duration: float,
    ) -> None:
        try:
            metric = ExecutionMetric(
                execution_id=str(uuid.uuid4()),
                plan_id=plan.id,
                intent=plan.intent or "unknown",
                provider=plan.metadata.get("provider", "unknown"),
                model=plan.metadata.get("model", "unknown"),
                started_at=(result.started_at or datetime.now(timezone.utc)),
                duration=duration,
                status=result.status,
                retry_count=result.retries,
                error=result.error,
                step_count=len(plan.steps),
                metadata=dict(plan.metadata or {}),
            )
            self.metrics_store.save(metric)
        except Exception as exc:
            logger.warning("No se pudo guardar métrica: %s", exc)

    def _apply_plan_state(self, plan: ExecutionPlan, result: ExecutionResult) -> None:
        if result.is_success:
            plan.mark_completed()
        elif result.is_partial:
            plan.mark_partial()
        elif result.is_failure:
            plan.mark_failed(result.error or "Plan failed")
        elif result.is_cancelled:
            plan.mark_cancelled()
        elif getattr(result, "is_retry", False):
            logger.error("Intento de finalizar plan en retry | plan=%s", plan.id)

    def _update_metrics(self, result: ExecutionResult) -> None:
        if result.is_success:
            self.metrics["success"] += 1
        elif result.is_partial:
            self.metrics["partial"] += 1
        elif result.is_failure:
            self.metrics["failed"] += 1
        elif result.is_cancelled:
            self.metrics["cancelled"] += 1

    def get_metrics(self) -> dict[str, int]:
        return dict(self.metrics)

    def _fail(self, plan: ExecutionPlan, error: str) -> ExecutionResult:
        logger.error("Plan %s falló: %s", plan.id, error)
        return ExecutionResult.fail(
            plan_id=plan.id,
            error=error,
            executor=self.name,
        )

    def _post_execution_check(self, plan: ExecutionPlan) -> ExecutionResult:
        # Si fue cancelado, terminamos
        if ExecutionPlan.status == "cancelled":
            return ExecutionResult(False, "Plan cancelado durante la ejecución.")

        # Post-validation (Fase 3 Action)
        if plan.metadata.get("executed_tools"):
            from core.analysis.validation_runner import ValidationRunner
            val_res = ValidationRunner().run_post_step_validation(plan)
            if not val_res.get("ok"):
                # Podemos dejar el plan marcado con warning o error si el linter falló
                logger.warning("Post-validation detectó errores. Revisar lint_error.")
                return ExecutionResult(False, str(val_res.get("error", "Linter fail")))

        return ExecutionResult(
            plan.status in ("completed", "success"),
            plan.error or "Plan ejecutado completamente.",
        )

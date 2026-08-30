import logging
import time
import uuid
from datetime import datetime, timezone

from core.analysis.validation_runner import ValidationRunner
from core.analytics.models import ExecutionMetric
from core.execution_plan import ExecutionPlan
from core.execution_result import ExecutionResult


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
                error=result.error
                or "La ejecución terminó en retry inesperadamente.",
                executor=result.executor or self.name,
                retries=result.retries,
                metadata={
                    **dict(result.metadata or {}),
                    "invalid_terminal_retry": True,
                },
                started_at=started_at,
            )

        finished_at = datetime.now(timezone.utc)
        result.set_execution_window(
            started_at=started_at,
            finished_at=finished_at,
        )

        # Post-validation antes de aplicar el estado final del plan.
        if result.is_success or result.is_partial:
            val_res = self._post_execution_check(plan)

            if val_res.is_partial:
                result = ExecutionResult.partial(
                    plan_id=plan.id,
                    result=result.result,
                    error=(
                        (result.error or "")
                        + " | Linter warning: "
                        + str(val_res.error)
                    ),
                    executor=result.executor or self.name,
                    retries=result.retries,
                    metadata={
                        **dict(result.metadata or {}),
                        "post_check": "lint_failed",
                    },
                    started_at=result.started_at or started_at,
                )
            elif not val_res.is_success:
                result.error = (
                    (result.error or "")
                    + " | Linter warning: "
                    + str(val_res.error)
                )

        self._apply_plan_state(plan, result)

        duration = max(
            0.0,
            round(time.monotonic() - started_monotonic, 3),
        )

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
                started_at=(
                    result.started_at
                    or datetime.now(timezone.utc)
                ),
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

    def _apply_plan_state(
        self,
        plan: ExecutionPlan,
        result: ExecutionResult,
    ) -> None:
        if result.is_success:
            plan.mark_completed()
        elif result.is_partial:
            plan.mark_partial()
        elif result.is_failure:
            plan.mark_failed(result.error or "Plan failed")
        elif result.is_cancelled:
            plan.mark_cancelled()
        elif getattr(result, "is_retry", False):
            logger.error(
                "Intento de finalizar plan en retry | plan=%s",
                plan.id,
            )

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

    def _fail(
        self,
        plan: ExecutionPlan,
        error: str,
    ) -> ExecutionResult:
        logger.error("Plan %s falló: %s", plan.id, error)

        return ExecutionResult.fail(
            plan_id=plan.id,
            error=error,
            executor=self.name,
        )

    def _post_execution_check(
        self,
        plan: ExecutionPlan,
    ) -> ExecutionResult:
        """
        Chequeo post-ejecución (linter / validación opcional).

        Siempre devuelve un ExecutionResult válido con plan_id,
        status y executor.
        """
        plan_id = getattr(plan, "id", None) or "unknown"

        status = str(
            getattr(plan, "status", "") or ""
        ).strip().lower()

        if status == "cancelled":
            return ExecutionResult.cancelled(
                plan_id=plan_id,
                executor=self.name,
            )

        if not plan.metadata.get("executed_tools"):
            return ExecutionResult.success(
                plan_id=plan_id,
                result={"post_check": "skipped"},
                executor=self.name,
                metadata={"post_check": "skipped"},
            )

        try:
            val_res = ValidationRunner().run_post_step_validation(plan)
        except Exception as exc:
            logger.warning(
                "Post-validation no disponible: %s",
                exc,
            )

            return ExecutionResult.success(
                plan_id=plan_id,
                result={
                    "post_check": "skipped",
                    "reason": str(exc),
                },
                executor=self.name,
                metadata={"post_check": "skipped"},
            )

        if not isinstance(val_res, dict):
            val_res = {
                "ok": False,
                "error": "validación inválida",
            }

        if not val_res.get("ok"):
            err = str(
                val_res.get("error") or "Linter fail"
            )

            logger.warning(
                "Post-validation detectó errores. "
                "Revisar lint_error."
            )

            plan.metadata["lint_error"] = err

            return ExecutionResult.partial(
                plan_id=plan_id,
                result=val_res,
                error=err,
                executor=self.name,
                metadata={
                    "post_check": "lint_failed",
                },
            )

        return ExecutionResult.success(
            plan_id=plan_id,
            result={"post_check": "ok"},
            executor=self.name,
            metadata={"post_check": "ok"},
        )

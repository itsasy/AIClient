from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.evaluation_result import EvaluationResult
from core.execution_result import ExecutionResult
from core.execution_step import ExecutionStep
from core.retry_decision import RetryDecision


@dataclass
class RetryPolicy:
    """
    Única autoridad sobre si se debe reintentar.

    No ejecuta nada. Solo decide.
    """

    default_delay: float = 0.5
    retry_on_self_critic_fail: bool = True
    retry_on_timeout: bool = True
    retry_on_execution_failure: bool = True
    retry_on_unavailable_evaluation: bool = False

    def decide(
        self,
        *,
        execution_result: ExecutionResult,
        evaluation: EvaluationResult | None = None,
        step: ExecutionStep | None = None,
        current_retries: int = 0,
        max_retries: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> RetryDecision:
        """
        Decide si corresponde reintentar.
        """

        # Ya no quedan intentos
        if current_retries >= max_retries:
            return RetryDecision.no(
                reason="Reintentos agotados",
                metadata={"current_retries": current_retries, "max_retries": max_retries},
            )

        # Cancelado → no retry
        if execution_result.is_cancelled:
            return RetryDecision.no(reason="Ejecución cancelada")

        # Success / partial terminal → no retry
        if execution_result.is_success or execution_result.is_partial:
            return RetryDecision.no(reason="Resultado terminal exitoso o parcial")

        # SelfCritic pidió retry explícitamente
        if execution_result.is_retry:
            return RetryDecision.yes(
                reason=execution_result.error or "SelfCritic solicitó reintento",
                delay_seconds=self.default_delay,
                metadata={"source": "execution_result.retry"},
            )

        # Evaluación fallida
        if evaluation is not None and evaluation.is_failed:
            if self.retry_on_self_critic_fail:
                return RetryDecision.yes(
                    reason=evaluation.reason or "Evaluación fallida",
                    delay_seconds=self.default_delay,
                    metadata={
                        "source": "evaluation.failed",
                        "issues": evaluation.issues,
                        "corrections": evaluation.corrections,
                    },
                )
            return RetryDecision.no(reason="Evaluación fallida y política no permite retry")

        # Evaluación unavailable
        if evaluation is not None and evaluation.is_unavailable:
            if self.retry_on_unavailable_evaluation:
                return RetryDecision.yes(
                    reason="Evaluación no disponible",
                    delay_seconds=self.default_delay,
                    metadata={"source": "evaluation.unavailable"},
                )
            return RetryDecision.no(reason="Evaluación no disponible")

        # Timeout
        is_timeout = bool(
            (execution_result.metadata or {}).get("timeout")
            or "timeout" in str(execution_result.error or "").lower()
        )
        if is_timeout and self.retry_on_timeout:
            return RetryDecision.yes(
                reason="Timeout de step/plan",
                delay_seconds=self.default_delay,
                metadata={"source": "timeout"},
            )

        # Fallo de ejecución genérico
        if execution_result.is_failure and self.retry_on_execution_failure:
            return RetryDecision.yes(
                reason=execution_result.error or "Fallo de ejecución",
                delay_seconds=self.default_delay,
                metadata={"source": "execution_failure"},
            )

        return RetryDecision.no(
            reason="No se cumplen condiciones de reintento",
            metadata={"status": execution_result.status},
        )

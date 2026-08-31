from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RetryDecision:
    should_retry: bool
    reason: str = ""
    max_retries: int = 0
    attempt: int = 0
    delay_seconds: float = 0.0

    def to_dict(self) -> dict:
        return {
            "should_retry": self.should_retry,
            "reason": self.reason,
            "max_retries": self.max_retries,
            "attempt": self.attempt,
            "delay_seconds": self.delay_seconds,
        }


class RetryPolicy:
    """
    Decide si un step/plan debe reintentarse.
    No ejecuta el step. Solo política.
    """

    name = "retry_policy"

    NON_RETRYABLE_MARKERS = (
        "allprovidersfailed",
        "todos los proveedores llm fallaron",
        "path traversal",
        "ruta fuera del proyecto",
        "content vacío",
        "write_file: content vacío",
        "no se proporcionó contenido",
        "permission denied",
        "operation not permitted",
        "módulo no permitido",
        "intent no soportado",
        "missing 1 required positional argument",
    )

    def decide(
        self,
        *,
        plan: Any = None,
        step: Any | None = None,
        error: str | Exception | None = None,
        execution_result: Any | None = None,
        result: Any | None = None,
        attempt: int = 0,
        evaluation: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> RetryDecision:
        """
        Firma amplia a propósito: el engine puede pasar
        execution_result / result / error / evaluation.
        kwargs absorbe claves futuras sin TypeError.
        """
        if kwargs:
            logger.debug("RetryPolicy.decide kwargs extra: %s", list(kwargs.keys()))

        max_retries = self._max_retries(plan, step)
        err_text = self._extract_error(
            error=error,
            execution_result=execution_result if execution_result is not None else result,
        )
        err_lower = err_text.lower()

        # evaluation puede venir en kwargs o embebida en result
        if evaluation is None:
            evaluation = self._extract_evaluation(execution_result or result)

        if attempt >= max_retries:
            return RetryDecision(
                should_retry=False,
                reason=f"max_retries alcanzado ({max_retries})",
                max_retries=max_retries,
                attempt=attempt,
            )

        if self._is_non_retryable(err_lower):
            logger.info(
                "Retry denegado (non-retryable) | attempt=%s | error=%s",
                attempt,
                err_text[:200],
            )
            return RetryDecision(
                should_retry=False,
                reason=f"error no reintentable: {err_text[:120]}",
                max_retries=max_retries,
                attempt=attempt,
            )

        if evaluation and evaluation.get("pass") is False:
            if max_retries > 0 and attempt < max_retries:
                return RetryDecision(
                    should_retry=True,
                    reason="self_critic no pasó; aplicar corrections",
                    max_retries=max_retries,
                    attempt=attempt,
                )
            return RetryDecision(
                should_retry=False,
                reason="self_critic falló y no hay retries",
                max_retries=max_retries,
                attempt=attempt,
            )

        # Si el result ya es success, no retry
        if self._is_success(execution_result or result):
            return RetryDecision(
                should_retry=False,
                reason="resultado exitoso",
                max_retries=max_retries,
                attempt=attempt,
            )

        if self._is_transient(err_lower):
            return RetryDecision(
                should_retry=True,
                reason="error transitorio",
                max_retries=max_retries,
                attempt=attempt,
            )

        if max_retries > 0 and attempt < max_retries and err_text:
            return RetryDecision(
                should_retry=True,
                reason="reintento genérico",
                max_retries=max_retries,
                attempt=attempt,
            )

        return RetryDecision(
            should_retry=False,
            reason="sin criterio de retry",
            max_retries=max_retries,
            attempt=attempt,
        )

    def _extract_error(
        self,
        *,
        error: Any,
        execution_result: Any,
    ) -> str:
        if error is not None:
            return str(error).strip()

        if execution_result is None:
            return ""

        # ExecutionResult-like
        for attr in ("error", "message"):
            val = getattr(execution_result, attr, None)
            if val:
                return str(val).strip()

        if isinstance(execution_result, dict):
            for key in ("error", "message", "reason"):
                if execution_result.get(key):
                    return str(execution_result[key]).strip()

        # fallback: str del objeto si parece fallido
        status = getattr(execution_result, "status", None)
        if status is None and isinstance(execution_result, dict):
            status = execution_result.get("status")
        if status and str(status).lower() in {
            "failed",
            "failure",
            "error",
            "cancelled",
        }:
            return str(status)

        return ""

    @staticmethod
    def _extract_evaluation(execution_result: Any) -> dict[str, Any] | None:
        if execution_result is None:
            return None
        meta = getattr(execution_result, "metadata", None)
        if isinstance(meta, dict) and isinstance(meta.get("evaluation"), dict):
            return meta["evaluation"]
        if isinstance(execution_result, dict):
            ev = execution_result.get("evaluation")
            if isinstance(ev, dict):
                return ev
        return None

    @staticmethod
    def _is_success(execution_result: Any) -> bool:
        if execution_result is None:
            return False
        if getattr(execution_result, "is_success", None) is True:
            return True
        status = getattr(execution_result, "status", None)
        if status is None and isinstance(execution_result, dict):
            status = execution_result.get("status")
            if execution_result.get("ok") is True:
                return True
        return str(status or "").lower() in {"completed", "success", "ok"}

    def _max_retries(self, plan: Any, step: Any | None) -> int:
        if plan is not None and hasattr(plan, "get_max_retries"):
            try:
                return int(plan.get_max_retries())
            except Exception:
                pass
        policy = getattr(plan, "execution_policy", None) or {}
        try:
            return max(0, int(policy.get("max_retries", 0)))
        except (TypeError, ValueError):
            return 0

    def _is_non_retryable(self, err_lower: str) -> bool:
        if not err_lower:
            return False
        return any(m in err_lower for m in self.NON_RETRYABLE_MARKERS)

    @staticmethod
    def _is_transient(err_lower: str) -> bool:
        markers = (
            "timeout",
            "timed out",
            "503",
            "502",
            "504",
            "429",
            "rate limit",
            "temporarily unavailable",
            "connection reset",
            "connect error",
            "network",
        )
        return any(m in err_lower for m in markers)

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
    )

    def decide(
        self,
        *,
        plan: Any,
        step: Any | None = None,
        error: str | Exception | None = None,
        attempt: int = 0,
        evaluation: dict[str, Any] | None = None,
    ) -> RetryDecision:
        max_retries = self._max_retries(plan, step)
        err_text = str(error or "").strip()
        err_lower = err_text.lower()

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

        # SelfCritic falló con correcciones → permitir 1 retry si policy lo permite
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

        # Timeout / 5xx / red: reintentar solo si queda cupo
        if self._is_transient(err_lower):
            return RetryDecision(
                should_retry=True,
                reason="error transitorio",
                max_retries=max_retries,
                attempt=attempt,
            )

        # Por defecto: reintentar solo si max_retries > 0 y attempt < max
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

    def _max_retries(self, plan: Any, step: Any | None) -> int:
        # Step puede fijar timeout/metadata; policy del plan manda
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

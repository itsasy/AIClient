from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from core.execution_step import ExecutionStep

class PlanLifecycleMixin:
    @property
    def is_terminal(self) -> bool:
        return self.status in {
            "completed",
            "partial",
            "failed",
            "cancelled",
        }

    @property
    def is_success(self) -> bool:
        return self.status == "completed"

    @property
    def is_failed(self) -> bool:
        return self.status == "failed"

    @property
    def is_partial(self) -> bool:
        return self.status == "partial"

    @property
    def is_running(self) -> bool:
        return self.status == "running"

    @property
    def is_pending(self) -> bool:
        return self.status == "pending"

    @property
    def is_planned(self) -> bool:
        return self.status == "planned"

    @property
    def is_validated(self) -> bool:
        return self.status == "validated"

    def _set_status(
        self,
        status: str,
    ) -> None:
        self.status = self.normalize_status(status)

    def mark_planned(self) -> None:
        self._set_status("planned")

    def mark_validated(self) -> None:
        errors = self.validate()

        if errors:
            raise ValueError("No se puede validar ExecutionPlan: " + "; ".join(errors))

        self._set_status("validated")

    def mark_running(self) -> None:
        if self.status not in {
            "planned",
            "validated",
            "running",
        }:
            raise ValueError("ExecutionPlan debe estar planned o " "validated antes de ejecutarse.")

        self._set_status("running")

    def mark_completed(
        self,
        result: Any = None,
    ) -> None:
        self.result = result
        self.error = None
        self._set_status("completed")

    def mark_partial(
        self,
        result: Any = None,
        error: str | None = None,
    ) -> None:
        self.result = result
        self.error = str(error) if error is not None else None
        self._set_status("partial")

    def mark_failed(self, error: str | None = None) -> None:
        """
        Marca el plan como fallido.

        error puede ser None; se normaliza a un mensaje no vacío
        para no romper callers y mantener self.error siempre definido.
        """
        msg = (error or "").strip() or "Plan failed"
        self.result = None
        self.error = msg
        self.metadata["last_error"] = msg
        self._set_status("failed")

    def mark_cancelled(
        self,
        reason: str | None = None,
    ) -> None:
        if reason:
            self.metadata["cancel_reason"] = str(reason)

        self._set_status("cancelled")


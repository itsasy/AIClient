from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from core.execution_step import ExecutionStep

class PlanGovernanceMixin:
    def _normalize_governance(self) -> None:
        mode = (
            str(
                self.governance.get(
                    "mode",
                    "safe",
                )
            )
            .lower()
            .strip()
        )

        if mode not in self.VALID_GOVERNANCE_MODES:
            raise ValueError(
                f"Modo de governance inválido: {mode}. "
                f"Modos permitidos: "
                f"{sorted(self.VALID_GOVERNANCE_MODES)}"
            )

        self.governance["mode"] = mode

        for key in (
            "allow_shell",
            "allow_network",
            "allow_write",
            "allow_sudo",
        ):
            value = self.governance.get(
                key,
                False,
            )

            if not isinstance(value, bool):
                raise ValueError(f"governance.{key} debe ser booleano.")

            self.governance[key] = value

    def is_safe_mode(self) -> bool:
        return (
            self.governance.get(
                "mode",
                "safe",
            )
            == "safe"
        )

    def is_powerful_mode(self) -> bool:
        return (
            self.governance.get(
                "mode",
                "safe",
            )
            == "powerful"
        )

    def allows_shell(self) -> bool:
        return bool(
            self.governance.get(
                "allow_shell",
                False,
            )
        )

    def allows_network(self) -> bool:
        return bool(
            self.governance.get(
                "allow_network",
                False,
            )
        )

    def allows_write(self) -> bool:
        return bool(
            self.governance.get(
                "allow_write",
                False,
            )
        )

    def allows_sudo(self) -> bool:
        return bool(
            self.governance.get(
                "allow_sudo",
                False,
            )
        )

    def _normalize_execution_policy(self) -> None:
        autonomous = self.execution_policy.get(
            "autonomous",
            False,
        )

        if not isinstance(autonomous, bool):
            raise ValueError("execution_policy.autonomous " "debe ser booleano.")

        self.execution_policy["autonomous"] = autonomous

        max_retries = self.execution_policy.get(
            "max_retries",
            2,
        )

        if isinstance(max_retries, bool) or not isinstance(max_retries, int) or max_retries < 0:
            raise ValueError(
                "execution_policy.max_retries debe ser " "un entero mayor o igual a cero."
            )

        self.execution_policy["max_retries"] = max_retries

        requires_approval = self.execution_policy.get(
            "requires_approval",
            False,
        )

        if not isinstance(requires_approval, bool):
            raise ValueError("execution_policy.requires_approval " "debe ser booleano.")

        self.execution_policy["requires_approval"] = requires_approval

        stop_on_error = self.execution_policy.get(
            "stop_on_error",
            True,
        )

        if not isinstance(stop_on_error, bool):
            raise ValueError("execution_policy.stop_on_error " "debe ser booleano.")

        self.execution_policy["stop_on_error"] = stop_on_error

        timeout = self.execution_policy.get(
            "timeout",
            300,
        )

        if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout <= 0:
            raise ValueError("execution_policy.timeout debe ser " "un entero mayor que cero.")

        self.execution_policy["timeout"] = timeout

    def is_autonomous(self) -> bool:
        return bool(
            self.execution_policy.get(
                "autonomous",
                False,
            )
        )

    def get_max_retries(self) -> int:
        return int(
            self.execution_policy.get(
                "max_retries",
                2,
            )
        )

    def requires_approval(self) -> bool:
        return bool(
            self.execution_policy.get(
                "requires_approval",
                False,
            )
        )

    def should_stop_on_error(self) -> bool:
        return bool(
            self.execution_policy.get(
                "stop_on_error",
                True,
            )
        )

    def get_timeout(self) -> int:
        return int(
            self.execution_policy.get(
                "timeout",
                300,
            )
        )


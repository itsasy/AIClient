from __future__ import annotations

import subprocess
from typing import Any

from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep
from core.tools.security_policy import SecurityPolicy
from skills.base import Skill


class ShellSkill(Skill):
    """
    Ejecuta comandos shell bajo SecurityPolicy.

    No decide si el comando es buena idea: solo aplica política
    y ejecuta si está permitido.
    """

    name = "shell"
    description = "Ejecuta un comando shell con restricciones de seguridad."
    version = "2.1"
    capabilities = (
        "shell",
        "command_execution",
    )

    def execute(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        params = step.params or {}

        command = params.get("command") or params.get("cmd") or params.get("task") or ""
        command = str(command).strip()

        if not command:
            return {
                "ok": False,
                "result": None,
                "error": "No se proporcionó comando.",
            }

        # 1. Governance del plan
        if not plan.allows_shell():
            return {
                "ok": False,
                "result": {
                    "command": command,
                    "blocked": True,
                },
                "error": "Ejecución de shell no permitida por la política del plan.",
            }

        # 2. SecurityPolicy (sudo, rm -rf /, patrones peligrosos)
        ok, err = SecurityPolicy.check_command(command, plan)
        if not ok:
            return {
                "ok": False,
                "result": {
                    "command": command,
                    "blocked": True,
                },
                "error": err,
            }

        timeout = int(params.get("timeout", 60) or 60)

        try:
            completed = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            return {
                "ok": completed.returncode == 0,
                "result": {
                    "command": command,
                    "returncode": completed.returncode,
                    "stdout": (completed.stdout or "")[:4000],
                    "stderr": (completed.stderr or "")[:2000],
                },
                "error": (
                    None
                    if completed.returncode == 0
                    else (completed.stderr or f"exit {completed.returncode}")
                ),
            }

        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "result": {
                    "command": command,
                    "blocked": False,
                },
                "error": f"Timeout ejecutando comando ({timeout}s).",
            }

        except Exception as e:
            return {
                "ok": False,
                "result": {
                    "command": command,
                },
                "error": str(e),
            }

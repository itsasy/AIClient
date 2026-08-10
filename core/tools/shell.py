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
    No decide si el comando es buena idea: solo aplica política.
    """

    name = "shell"
    description = "Ejecuta un comando shell con restricciones de seguridad."
    version = "2.0"
    capabilities = ("shell", "command_execution")

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

        ok, err = SecurityPolicy.check_command(command, plan)
        if not ok:
            return {
                "ok": False,
                "result": {"command": command, "blocked": True},
                "error": err,
            }

        try:
            completed = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=int(params.get("timeout", 60)),
            )
            return {
                "ok": completed.returncode == 0,
                "result": {
                    "command": command,
                    "returncode": completed.returncode,
                    "stdout": completed.stdout,
                    "stderr": completed.stderr,
                },
                "error": None if completed.returncode == 0 else completed.stderr,
            }
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "result": {"command": command},
                "error": "Timeout ejecutando comando.",
            }
        except Exception as e:
            return {
                "ok": False,
                "result": {"command": command},
                "error": str(e),
            }

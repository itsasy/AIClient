from __future__ import annotations

import subprocess
import tempfile

from pathlib import Path
from typing import Any

from core.config import Config

from core.execution_plan import (
    ExecutionPlan,
    ExecutionStep,
)

from skills.base import Skill


class CodeSandboxSkill(Skill):

    name = "sandbox"

    description = "Ejecuta código Python dentro de un contenedor Docker aislado."

    version = "2.0"

    capabilities = (
        "isolated_execution",
        "docker_execution",
        "secure_runtime",
    )

    def execute(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any],
    ) -> dict[str, Any]:

        params = step.params or {}

        code = params.get(
            "code",
            "",
        )

        timeout = params.get(
            "timeout",
            int(Config.SANDBOX_TIMEOUT),
        )

        if not code.strip():

            return {
                "ok": False,
                "result": None,
                "error": "Código vacío.",
            }

        if not self._docker_available():

            return {
                "ok": False,
                "result": None,
                "error": "Docker no está disponible.",
            }

        try:

            with tempfile.TemporaryDirectory() as tmpdir:

                script = Path(tmpdir) / "script.py"

                script.write_text(
                    code,
                    encoding="utf-8",
                )

                command = [
                    "docker",
                    "run",
                    "--rm",
                    "--network",
                    "none",
                    "--memory",
                    Config.SANDBOX_MEMORY,
                    "--cpus",
                    Config.SANDBOX_CPU,
                    "--user",
                    "nobody",
                    "--read-only",
                    "--mount",
                    (f"type=bind," f"source={script}," f"target=/script.py," "ro"),
                    Config.SANDBOX_IMAGE,
                    "python",
                    "/script.py",
                ]

                process = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )

                output = process.stdout.strip() or process.stderr.strip()

                return {
                    "ok": process.returncode == 0,
                    "result": {
                        "type": "sandbox_execution",
                        "output": output[:2000],
                        "returncode": process.returncode,
                    },
                    "error": (None if process.returncode == 0 else process.stderr.strip()),
                }

        except subprocess.TimeoutExpired:

            return {
                "ok": False,
                "result": None,
                "error": (f"Sandbox excedió timeout {timeout}s"),
            }

        except Exception as exc:

            return {
                "ok": False,
                "result": None,
                "error": str(exc),
            }

    def _docker_available(self) -> bool:

        try:

            result = subprocess.run(
                [
                    "docker",
                    "version",
                ],
                capture_output=True,
                timeout=5,
            )

            return result.returncode == 0

        except Exception:

            return False

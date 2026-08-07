from __future__ import annotations

import subprocess
import tempfile

from pathlib import Path
from typing import Any

from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep

from skills.base import Skill


class CodeExecutorSkill(Skill):

    name = "execute_code"

    description = "Ejecuta código Python en entorno temporal."

    version = "2.0"

    capabilities = (
        "code_execution",
        "python_runtime",
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
            10,
        )

        if not code.strip():

            return {
                "ok": False,
                "result": None,
                "error": "Código vacío.",
            }

        try:

            with tempfile.TemporaryDirectory() as tmpdir:

                script = Path(tmpdir) / "script.py"

                script.write_text(
                    code,
                    encoding="utf-8",
                )

                process = subprocess.run(
                    [
                        "python",
                        str(script),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=tmpdir,
                )

                success = process.returncode == 0

                return {
                    "ok": success,
                    "result": {
                        "type": "execution_result",
                        "stdout": process.stdout.strip(),
                        "stderr": process.stderr.strip(),
                        "returncode": process.returncode,
                    },
                    "error": (None if success else process.stderr.strip()),
                }

        except subprocess.TimeoutExpired:

            return {
                "ok": False,
                "result": None,
                "error": f"Tiempo máximo excedido: {timeout}s",
            }

        except Exception as exc:

            return {
                "ok": False,
                "result": None,
                "error": str(exc),
            }

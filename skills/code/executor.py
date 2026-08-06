from __future__ import annotations

import subprocess
import tempfile

from pathlib import Path
from typing import Any

from skills.base import Skill


class CodeExecutorSkill(Skill):

    name = "execute_code"

    description = "Ejecuta código Python " "en un entorno temporal aislado."

    version = "1.0"

    capabilities = ["code_execution"]

    def execute(
        self,
        code: str = "",
        timeout: int = 10,
        **kwargs: Any,
    ) -> dict[str, Any]:

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

                return {
                    "ok": process.returncode == 0,
                    "result": {
                        "type": "execution_result",
                        "stdout": process.stdout.strip(),
                        "stderr": process.stderr.strip(),
                        "returncode": process.returncode,
                    },
                    "error": (None if process.returncode == 0 else process.stderr.strip()),
                }

        except subprocess.TimeoutExpired:

            return {
                "ok": False,
                "result": None,
                "error": (f"Tiempo máximo excedido: {timeout}s"),
            }

        except Exception as exc:

            return {
                "ok": False,
                "result": None,
                "error": str(exc),
            }

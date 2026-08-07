from __future__ import annotations

import subprocess
import tempfile

from pathlib import Path
from typing import Any

from core.config import Config
from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep

from skills.base import Skill


class CodeSandboxSkill(Skill):
    """
    Ejecuta código Python dentro de un contenedor Docker aislado.

    Responsabilidades:

    - Ejecutar código aislado.
    - Aplicar límites básicos de ejecución.
    - Devolver resultado serializable.

    No:

    - Gestiona retries.
    - Decide políticas de seguridad globales.
    - Administra infraestructura Docker.
    """

    name = "sandbox"

    description = "Ejecuta código Python dentro de un contenedor Docker aislado."

    version = "2.2"

    capabilities = (
        "isolated_execution",
        "docker_execution",
        "secure_runtime",
    )

    MAX_CODE_SIZE = 100_000
    MAX_OUTPUT_SIZE = 4_000

    def __init__(self):

        self._docker_checked = False
        self._docker_available_cache = False

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

        timeout = self._resolve_timeout(
            params.get(
                "timeout",
                Config.SANDBOX_TIMEOUT,
            )
        )

        if not isinstance(code, str) or not code.strip():

            return self._error(
                "Código vacío.",
            )

        if len(code) > self.MAX_CODE_SIZE:

            return self._error(
                (
                    "El código supera el tamaño máximo permitido "
                    f"({self.MAX_CODE_SIZE} caracteres)."
                ),
            )

        if not self._docker_available():

            return self._error(
                "Docker no está disponible.",
            )

        try:

            with tempfile.TemporaryDirectory() as tmpdir:

                script = Path(tmpdir) / "script.py"

                script.write_text(
                    code,
                    encoding="utf-8",
                )

                process = subprocess.run(
                    self._build_command(
                        script,
                    ),
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False,
                )

                stdout = process.stdout.strip()
                stderr = process.stderr.strip()

                output = stdout or stderr or ""

                return {
                    "ok": process.returncode == 0,
                    "result": {
                        "type": "sandbox_execution",
                        "output": output[: self.MAX_OUTPUT_SIZE],
                        "returncode": process.returncode,
                        "timeout": timeout,
                    },
                    "error": (None if process.returncode == 0 else stderr[: self.MAX_OUTPUT_SIZE]),
                }

        except subprocess.TimeoutExpired:

            return self._error(
                f"Sandbox excedió timeout {timeout}s.",
            )

        except Exception as exc:

            return self._error(
                str(exc),
            )

    def _build_command(
        self,
        script: Path,
    ) -> list[str]:

        image = getattr(
            Config,
            "SANDBOX_IMAGE",
            "",
        )

        if not image:

            raise RuntimeError("SANDBOX_IMAGE no configurada.")

        memory = getattr(
            Config,
            "SANDBOX_MEMORY",
            "128m",
        )

        cpu = getattr(
            Config,
            "SANDBOX_CPU",
            "0.5",
        )

        return [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--memory",
            memory,
            "--cpus",
            cpu,
            "--pids-limit",
            "64",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--user",
            "nobody",
            "--read-only",
            "--mount",
            (f"type=bind," f"source={script}," "target=/script.py," "ro"),
            image,
            "python",
            "/script.py",
        ]

    def _resolve_timeout(
        self,
        value: Any,
    ) -> int:

        try:

            timeout = int(value)

        except Exception:

            timeout = int(
                Config.SANDBOX_TIMEOUT,
            )

        return max(
            timeout,
            1,
        )

    def _docker_available(
        self,
    ) -> bool:

        if self._docker_checked:

            return self._docker_available_cache

        self._docker_checked = True

        try:

            result = subprocess.run(
                [
                    "docker",
                    "version",
                ],
                capture_output=True,
                timeout=5,
                check=False,
            )

            self._docker_available_cache = result.returncode == 0

        except Exception:

            self._docker_available_cache = False

        return self._docker_available_cache

    def _error(
        self,
        message: str,
    ) -> dict[str, Any]:

        return {
            "ok": False,
            "result": None,
            "error": message,
        }

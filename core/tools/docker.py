from __future__ import annotations

import subprocess
import time

from typing import Any

from core.config import Config

from core.tools.base import Tool


class DockerTool(Tool):

    name = "docker"

    description = "Ejecuta operaciones Docker permitidas."

    version = "2.0"

    capabilities = (
        "docker_management",
        "container_operations",
    )

    SAFE_COMMANDS: tuple[str, ...] = (
        "docker ps",
        "docker images",
        "docker logs",
        "docker info",
        "docker inspect",
    )

    def execute(
        self,
        command: str,
        **kwargs,
    ) -> dict[str, Any]:

        command = command.strip()

        if Config.POWER_MODE == "safe" and command.startswith("sudo"):

            return {
                "ok": False,
                "result": {
                    "command": command,
                },
                "error": "Comando sudo bloqueado.",
            }

        if not command.startswith("docker "):

            return {
                "ok": False,
                "result": {
                    "command": command,
                },
                "error": "Debe ejecutar comandos Docker explícitos.",
            }

        if not any(
            command.startswith(
                allowed,
            )
            for allowed in self.SAFE_COMMANDS
        ):

            return {
                "ok": False,
                "result": {
                    "command": command,
                },
                "error": (f"Comando Docker no permitido: {command}"),
            }

        try:

            start = time.time()

            process = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=Config.DOCKER_TIMEOUT,
                cwd=Config.TARGET_PROJECT_ROOT,
            )

            duration = round(
                time.time() - start,
                3,
            )

            output = process.stdout.strip() or process.stderr.strip()

            return {
                "ok": process.returncode == 0,
                "result": {
                    "command": command,
                    "output": output[:1000],
                    "duration": duration,
                },
                "error": (None if process.returncode == 0 else output),
            }

        except Exception as exc:

            return {
                "ok": False,
                "result": {
                    "command": command,
                },
                "error": str(exc),
            }

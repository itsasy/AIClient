from __future__ import annotations

import subprocess
import time

from typing import Any

from core.config import Config

from core.tools.base import Tool


class ShellTool(Tool):

    name = "shell"

    description = "Ejecuta comandos shell con restricciones de seguridad."

    version = "2.0"

    capabilities = (
        "command_execution",
        "filesystem_access",
        "project_operations",
    )

    SAFE_PREFIXES: tuple[str, ...] = (
        "git status",
        "git log",
        "git branch",
        "git diff",
        "ls",
        "tree",
        "pwd",
        "echo ",
        "cat ",
        "find ",
        "grep ",
        "composer install",
        "composer require",
        "npm install",
        "npm run",
        "yarn install",
        "php artisan",
        "laravel new",
        "docker compose",
        "docker run",
        "docker exec",
        "npx ",
    )

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "El comando shell a ejecutar."
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout opcional en segundos."
                        }
                    },
                    "required": ["command"]
                }
            }
        }

    def execute(
        self,
        command: str,
        timeout: int | None = None,
        **kwargs,
    ) -> dict[str, Any]:

        command = command.strip()

        normalized = command.lower()

        if Config.POWER_MODE == "safe" and normalized.startswith("sudo"):

            return {
                "ok": False,
                "result": {
                    "command": command,
                },
                "error": "Comando sudo bloqueado en modo seguro.",
            }

        if not any(
            normalized.startswith(
                prefix.lower(),
            )
            for prefix in self.SAFE_PREFIXES
        ):

            return {
                "ok": False,
                "result": {
                    "command": command,
                },
                "error": (f"Comando bloqueado por seguridad: {command}"),
            }

        try:

            start = time.time()

            process = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=(timeout if timeout is not None else Config.SHELL_TIMEOUT),
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
                    "output": output[:1500],
                    "returncode": process.returncode,
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

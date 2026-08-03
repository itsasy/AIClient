from pathlib import Path
import subprocess
import time

from skills.base import Skill
from core.config import Config


class ShellTool(Skill):
    name = "shell"
    description = "Ejecuta comandos seguros"

    SAFE_PREFIXES = [
        "git status",
        "git log",
        "git branch",
        "git diff",
        "ls",
        "tree ",
        "pwd",
        "echo ",
        "cat ",
        "find ",
        "grep ",
        "composer ",
        "php ",
        "artisan ",
        "laravel new",
        "npm ",
        "yarn ",
        "docker compose",
        "docker run",
        "docker exec",
        "npx ",
        "npm ",
        "yarn ",
    ]

    def execute(self, command: str, timeout: int | None = None, **kwargs):
        command = command.strip()
        normalized = command.lower()

        if Config.POWER_MODE == "safe" and command.startswith("sudo"):
            return {
                "type": "shell_result",
                "payload": {
                    "ok": False,
                    "message": "Comando 'sudo' bloqueado en modo seguro",
                    "command": command,
                },
            }

        if not any(normalized.startswith(p.lower()) for p in self.SAFE_PREFIXES):
            return {
                "type": "shell_result",
                "payload": {
                    "ok": False,
                    "message": f"Comando bloqueado por seguridad: {command}",
                    "command": command,
                },
            }

        try:
            cwd = Config.TARGET_PROJECT_ROOT
            timeout_value = timeout if timeout is not None else Config.SHELL_TIMEOUT

            start = time.time()

            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout_value,
                cwd=cwd,
            )

            duration = round(time.time() - start, 3)

            output = result.stdout.strip() or result.stderr.strip()

            return {
                "type": "shell_result",
                "payload": {
                    "ok": result.returncode == 0,
                    "command": command,
                    "output": output[:1500],
                    "returncode": result.returncode,
                    "duration": duration,
                },
            }

        except Exception as e:
            return {
                "type": "shell_result",
                "payload": {
                    "ok": False,
                    "command": command,
                    "output": str(e),
                },
            }

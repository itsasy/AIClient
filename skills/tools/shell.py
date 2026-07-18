from pathlib import Path
import subprocess

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
    ]

    def execute(self, command: str, timeout: int | None = None, **kwargs):
        command = command.strip()
        normalized = command.lower()

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

            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout_value,
                cwd=cwd,
            )
            output = result.stdout.strip() or result.stderr.strip()
            return {
                "type": "shell_result",
                "payload": {
                    "ok": result.returncode == 0,
                    "command": command,
                    "output": output[:1500],
                    "returncode": result.returncode,
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

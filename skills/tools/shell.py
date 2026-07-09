from pathlib import Path
import subprocess

from skills.base import Skill


class ShellTool(Skill):
    name = "shell"
    description = "Ejecuta comandos seguros"

    SAFE_PREFIXES = ["git ", "ls", "tree ", "pwd", "echo ", "cat ", "find ", "grep "]
    SAFE_EXACT = ["git status", "git log --oneline -10", "git branch"]

    def execute(self, command: str, **kwargs):
        command = command.strip()
        normalized = command.lower()

        if not any(normalized.startswith(prefix.lower()) for prefix in self.SAFE_PREFIXES) and command not in self.SAFE_EXACT:
            return {
                "type": "shell_result",
                "payload": {
                    "ok": False,
                    "message": "Comando bloqueado por seguridad.",
                    "command": command,
                },
            }

        try:
            project_root = Path(__file__).resolve().parents[2]
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=12,
                cwd=project_root,
            )
            output = result.stdout.strip() or result.stderr.strip()
            return {
                "type": "shell_result",
                "payload": {
                    "ok": result.returncode == 0,
                    "command": command,
                    "output": output[:1200],
                    "returncode": result.returncode,
                },
            }
        except subprocess.TimeoutExpired:
            return {
                "type": "shell_result",
                "payload": {
                    "ok": False,
                    "command": command,
                    "output": "Comando timeout (demasiado lento)",
                    "timed_out": True,
                },
            }
        except Exception as exc:
            return {
                "type": "shell_result",
                "payload": {
                    "ok": False,
                    "command": command,
                    "output": f"Error: {exc}",
                },
            }

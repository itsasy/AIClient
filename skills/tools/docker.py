from skills.base import Skill
import subprocess


class DockerTool(Skill):
    name = "docker"
    description = "Operaciones Docker seguras"

    def execute(self, command: str, **kwargs):
        command = command.strip()
        if not command.startswith("docker"):
            command = f"docker {command}"

        safe_commands = [
            "docker ps",
            "docker images",
            "docker logs",
            "docker info",
            "docker inspect",
        ]
        if not any(command.startswith(sc) for sc in safe_commands):
            return {
                "type": "docker_result",
                "payload": {
                    "ok": False,
                    "message": f"Comando Docker no permitido: {command}",
                    "command": command,
                },
            }

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10,
            )
            output = result.stdout.strip() or result.stderr.strip()
            return {
                "type": "docker_result",
                "payload": {
                    "ok": result.returncode == 0,
                    "command": command,
                    "output": output[:1000],
                },
            }
        except Exception as e:
            return {
                "type": "docker_result",
                "payload": {
                    "ok": False,
                    "command": command,
                    "output": str(e),
                },
            }

from skills.base import Skill
import subprocess

class DockerTool(Skill):
    name = "docker"
    description = "Operaciones Docker seguras"

    def execute(self, action: str = "ps", **kwargs):
        safe_actions = {
            "ps": "docker ps",
            "images": "docker images",
            "logs": "docker logs",
            "status": "docker info --format '{{.ServerVersion}}'",
        }
        cmd = safe_actions.get(action, "docker ps")
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            return {
                "type": "docker_result",
                "payload": {
                    "ok": result.returncode == 0,
                    "action": action,
                    "output": result.stdout.strip()[:1000],
                }
            }
        except Exception as e:
            return {"type": "docker_result", "payload": {"ok": False, "error": str(e)}}
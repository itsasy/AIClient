import subprocess
import tempfile
from pathlib import Path

from skills.base import Skill
from core.config import Config


class CodeSandboxSkill(Skill):
    name = "sandbox"
    description = (
        "Ejecuta código Python de forma aislada dentro de un contenedor Docker"
    )

    def execute(self, code: str, **kwargs):
        if not code or not code.strip():
            return {
                "type": "sandbox_result",
                "payload": {"ok": False, "output": "Código vacío"},
            }

        if not self._docker_available():
            return {
                "type": "sandbox_result",
                "payload": {
                    "ok": False,
                    "output": (
                        "❌ Docker no está instalado o no está en el PATH.\n"
                        "Instala Docker Desktop o Docker Engine para usar el sandbox aislado."
                    ),
                },
            }

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                script_path = Path(tmpdir) / "script.py"
                script_path.write_text(code, encoding="utf-8")

                docker_cmd = [
                    "docker",
                    "run",
                    "--rm",
                    "--network",
                    "none",
                    "--memory",
                    Config.SANDBOX_MEMORY,
                    "--cpus",
                    Config.SANDBOX_CPU,
                    "--user",
                    "nobody",
                    "--read-only",
                    "--mount",
                    f"type=bind,source={script_path},target=/script.py,ro",
                    Config.SANDBOX_IMAGE,
                    "python",
                    "/script.py",
                ]

                timeout = kwargs.get("timeout", int(Config.SANDBOX_TIMEOUT))
                result = subprocess.run(
                    docker_cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=tmpdir,
                )

                stdout = result.stdout.strip()
                stderr = result.stderr.strip()
                output = stdout if stdout else stderr

                return {
                    "type": "sandbox_result",
                    "payload": {
                        "ok": result.returncode == 0,
                        "output": output[:1500],
                        "error": stderr if result.returncode != 0 else "",
                        "returncode": result.returncode,
                    },
                }

        except subprocess.TimeoutExpired:
            return {
                "type": "sandbox_result",
                "payload": {
                    "ok": False,
                    "output": f"⏱️ Timeout de ejecución ({timeout}s). El código se ha detenido.",
                },
            }

        except FileNotFoundError:
            return {
                "type": "sandbox_result",
                "payload": {
                    "ok": False,
                    "output": "❌ Docker no encontrado. Asegúrate de que Docker esté instalado y en el PATH.",
                },
            }

        except Exception as e:
            return {
                "type": "sandbox_result",
                "payload": {
                    "ok": False,
                    "output": f"❌ Error inesperado en el sandbox: {e}",
                },
            }

    def _docker_available(self) -> bool:
        try:
            subprocess.run(
                ["docker", "version", "--format", "{{.Server.Version}}"],
                capture_output=True,
                timeout=5,
                check=False,
            )
            return True
        except (
            subprocess.TimeoutExpired,
            FileNotFoundError,
            subprocess.CalledProcessError,
        ):
            return False

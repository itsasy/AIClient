from skills.base import Skill
import subprocess
import tempfile
from pathlib import Path

class CodeSandboxSkill(Skill):
    name = "sandbox"
    description = "Ejecuta código de forma aislada y segura"

    def execute(self, code: str, **kwargs):
        if not code or not code.strip():
            return {"type": "sandbox_result", "payload": {"ok": False, "output": "Código vacío"}}

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                script = Path(tmpdir) / "sandbox.py"
                script.write_text(code, encoding="utf-8")

                result = subprocess.run(
                    ["python", "-u", str(script)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=tmpdir,
                )

                return {
                    "type": "sandbox_result",
                    "payload": {
                        "ok": result.returncode == 0,
                        "output": result.stdout.strip(),
                        "error": result.stderr.strip(),
                    }
                }
        except subprocess.TimeoutExpired:
            return {"type": "sandbox_result", "payload": {"ok": False, "output": "Timeout de ejecución"}}
        except Exception as e:
            return {"type": "sandbox_result", "payload": {"ok": False, "output": str(e)}}
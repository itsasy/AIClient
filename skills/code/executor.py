from skills.base import Skill
import subprocess
import tempfile
from pathlib import Path

class CodeExecutorSkill(Skill):
    name = "execute_code"
    description = "Ejecuta código Python de forma aislada"

    def execute(self, code: str, **kwargs):
        if not code or not code.strip():
            return {"type": "execution_result", "payload": {"ok": False, "output": "Código vacío"}}

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                script = Path(tmpdir) / "script.py"
                script.write_text(code, encoding="utf-8")

                result = subprocess.run(
                    ["python", str(script)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=tmpdir,
                )

                return {
                    "type": "execution_result",
                    "payload": {
                        "ok": result.returncode == 0,
                        "output": result.stdout.strip(),
                        "error": result.stderr.strip(),
                    }
                }
        except Exception as e:
            return {"type": "execution_result", "payload": {"ok": False, "output": str(e)}}
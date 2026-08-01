from pathlib import Path
from skills.base import Skill


class WriteFileSkill(Skill):
    name = "write_file"
    description = "Escribe contenido en un archivo del sistema. No genera contenido."

    def execute(self, path: str, content: str, **kwargs):
        if not content:
            return {
                "type": "write_file_result",
                "payload": {
                    "ok": False,
                    "error": "No se proporcionó contenido para escribir. La skill 'write_file' solo escribe, no genera contenido.",
                },
            }

        filepath = Path(path).expanduser().resolve()
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(content, encoding="utf-8")
            return {
                "type": "write_file_result",
                "payload": {
                    "ok": True,
                    "path": str(filepath),
                    "message": f"Archivo creado correctamente en {filepath}",
                },
            }
        except Exception as e:
            return {
                "type": "write_file_result",
                "payload": {"ok": False, "error": str(e)},
            }

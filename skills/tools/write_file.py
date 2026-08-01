from pathlib import Path
from skills.base import Skill
from llm.router import LLMRouter


class WriteFileSkill(Skill):
    name = "write_file"
    description = "Escribe contenido en un archivo del sistema. Si no se proporciona contenido, lo genera usando el LLM."

    def execute(self, path: str, content: str = None, **kwargs):
        filepath = Path(path).expanduser().resolve()

        if content is None:
            prompt = f"Genera el contenido para el archivo '{filepath.name}'. El contenido debe ser apropiado para su extensión y uso. Devuelve SOLO el contenido, sin explicaciones ni markdown."
            try:
                content = LLMRouter.generate(task=prompt, skill_name="code")
            except Exception as e:
                return {
                    "type": "write_file_result",
                    "payload": {"ok": False, "error": f"No se pudo generar contenido: {e}"},
                }

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

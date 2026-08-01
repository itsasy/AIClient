import logging
from pathlib import Path
from skills.base import Skill
from llm.router import LLMRouter

logger = logging.getLogger(__name__)


class WriteFileSkill(Skill):
    name = "write_file"
    description = "Escribe contenido en un archivo del sistema. Si no se proporciona contenido, lo genera usando el LLM."

    def execute(
        self,
        path: str,
        content: str | None = None,
        task: str | None = None,
        **kwargs,
    ):
        filepath = Path.cwd() / path
        filepath = filepath.expanduser().resolve()

        if content is None:
            prompt = task or (
                f"Genera únicamente el contenido del archivo '{filepath.name}'. "
                "Devuelve sólo el contenido, sin markdown."
            )

            content = LLMRouter.generate(
                task=prompt,
                skill_name="code",
            )

        try:
            logger.info(
                "Creando archivo %s",
                filepath,
            )

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

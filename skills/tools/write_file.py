import logging
from pathlib import Path

from skills.base import Skill

logger = logging.getLogger(__name__)


class WriteFileSkill(Skill):

    name = "write_file"

    description = "Escribe contenido en un archivo del sistema."

    def execute(
        self,
        path: str,
        content: str,
        **kwargs,
    ):

        filepath = Path.cwd() / path
        filepath = filepath.expanduser().resolve()

        try:

            logger.info(
                "Creando archivo %s",
                filepath,
            )

            filepath.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            filepath.write_text(
                content,
                encoding="utf-8",
            )

            return {
                "type": "write_file_result",
                "payload": {
                    "ok": True,
                    "path": str(filepath),
                    "message": (f"Archivo creado correctamente " f"en {filepath}"),
                },
            }

        except Exception as e:

            logger.exception("Error escribiendo archivo")

            return {
                "type": "write_file_result",
                "payload": {
                    "ok": False,
                    "error": str(e),
                },
            }

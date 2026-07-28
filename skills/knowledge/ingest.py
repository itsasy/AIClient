from pathlib import Path
from skills.base import Skill
from core.document_ingestor import DocumentIngestor


class IngestDocumentSkill(Skill):
    name = "ingest"
    description = "Ingiere un documento (PDF, DOCX, TXT, imagen) y lo guarda en Engram"

    def execute(self, filepath: str, tags: str = "", **kwargs):
        path = Path(filepath).expanduser()
        if not path.exists():
            return {
                "type": "ingest_result",
                "payload": {
                    "ok": False,
                    "output": f"❌ Archivo no encontrado: {filepath}",
                },
            }

        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
        ingestor = DocumentIngestor()
        success = ingestor.ingest_file(path, tags=tag_list)

        return {
            "type": "ingest_result",
            "payload": {
                "ok": success,
                "filepath": str(path),
                "output": (
                    f"✅ Documento ingerido: {path.name}"
                    if success
                    else f"❌ Error ingiriendo: {path.name}"
                ),
            },
        }

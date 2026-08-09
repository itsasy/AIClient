from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.config import Config
from core.engram_memory import EngramMemory
from core.standards_learner import StandardsLearner


class MemoryExporter:
    """
    Exporta la memoria del sistema a un archivo portable.
    """

    def __init__(self):
        self.engram = EngramMemory()
        self.standards = StandardsLearner()

    def export(self, output_name: str = "aiclient_memory_export", format: str = "zip") -> Path:
        """
        Exporta la memoria a un archivo.
        """
        # Crear directorio temporal
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            export_dir = tmp_path / "aiclient_memory"

            # 1. Exportar estándares
            standards_path = export_dir / "standards.json"
            standards_path.write_text(
                json.dumps(self.standards.list_standards(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

            # 2. Exportar especificaciones
            specs_dir = export_dir / "specs"
            specs_dir.mkdir(parents=True, exist_ok=True)
            specs_src = Config.PROJECT_ROOT / ".specs"
            if specs_src.exists():
                for spec_file in specs_src.glob("*.json"):
                    shutil.copy(spec_file, specs_dir / spec_file.name)

            # 3. Exportar metadatos de Engram
            engram_db = Path.home() / ".engram" / "aiclient.db"
            if engram_db.exists():
                shutil.copy(engram_db, export_dir / "engram.db")

            # 4. Crear archivo de manifiesto
            manifest = {
                "version": "1.0",
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "components": ["standards", "specs", "engram"],
                "standards_count": len(self.standards.list_standards()),
                "specs_count": len(list(specs_src.glob("*.json"))) if specs_src.exists() else 0,
            }
            (export_dir / "manifest.json").write_text(
                json.dumps(manifest, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

            # 5. Empaquetar
            output_path = Path.cwd() / f"{output_name}.{format}"
            if format == "zip":
                with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    for file_path in export_dir.rglob("*"):
                        zf.write(file_path, file_path.relative_to(export_dir))
            elif format == "tar":
                import tarfile

                with tarfile.open(output_path, "w:gz") as tf:
                    tf.add(export_dir, arcname="aiclient_memory")
            else:
                raise ValueError(f"Formato no soportado: {format}")

            return output_path

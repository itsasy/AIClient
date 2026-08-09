from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.config import Config


class SnapshotManager:
    """
    Gestiona snapshots de archivos de memoria (standards, specs, etc.)
    para permitir rollback.
    """

    def __init__(self):
        self.snapshots_dir = Config.PROJECT_ROOT / ".memory" / "snapshots"
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

        # Archivos a versionar
        self.targets = [
            ("standards", Config.PROJECT_ROOT / ".standards.json"),
            ("specs", Config.PROJECT_ROOT / ".specs"),
        ]

    def snapshot(self, label: str | None = None) -> str:
        """
        Crea un snapshot de los archivos de memoria.
        Retorna el ID del snapshot.
        """
        snapshot_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        if label:
            snapshot_id = f"{label}_{snapshot_id}"

        snapshot_dir = self.snapshots_dir / snapshot_id
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        for name, path in self.targets:
            if path.exists():
                target = snapshot_dir / name
                if path.is_dir():
                    shutil.copytree(path, target, dirs_exist_ok=True)
                else:
                    shutil.copy2(path, target)

        # Guardar metadatos
        metadata = {
            "id": snapshot_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "label": label,
            "files": [name for name, _ in self.targets],
        }
        (snapshot_dir / "metadata.json").write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return snapshot_id

    def list_snapshots(self) -> list[dict[str, Any]]:
        """
        Lista los snapshots disponibles.
        """
        snapshots = []
        for d in sorted(self.snapshots_dir.iterdir(), reverse=True):
            if d.is_dir():
                metadata_path = d / "metadata.json"
                if metadata_path.exists():
                    data = json.loads(metadata_path.read_text(encoding="utf-8"))
                    snapshots.append(data)
                else:
                    snapshots.append(
                        {
                            "id": d.name,
                            "created_at": datetime.fromtimestamp(d.stat().st_mtime).isoformat(),
                            "label": None,
                        }
                    )
        return snapshots

    def rollback(self, snapshot_id: str) -> bool:
        """
        Restaura un snapshot.
        """
        snapshot_dir = self.snapshots_dir / snapshot_id
        if not snapshot_dir.exists():
            return False

        # Primero, crear un snapshot de seguridad antes de rollback
        self.snapshot("pre_rollback")

        for name, path in self.targets:
            source = snapshot_dir / name
            if source.exists():
                # Eliminar el destino actual
                if path.exists():
                    if path.is_dir():
                        shutil.rmtree(path)
                    else:
                        path.unlink()
                # Restaurar
                if source.is_dir():
                    shutil.copytree(source, path)
                else:
                    shutil.copy2(source, path)

        return True

    def latest(self) -> str | None:
        """Devuelve el ID del snapshot más reciente."""
        snapshots = self.list_snapshots()
        if snapshots:
            return snapshots[0]["id"]
        return None

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from core.config import Config
from core.engram_memory import EngramMemory

logger = logging.getLogger(__name__)


class SpecManager:
    """
    Gestiona especificaciones (Specs) para el flujo SDD.

    Fuente de verdad: archivos JSON en PROJECT_ROOT/.specs/
    Engram se usa solo como índice/referencia corta.
    """

    def __init__(self):
        self.engram = EngramMemory()
        self.specs_dir = Config.PROJECT_ROOT / ".specs"
        self.specs_dir.mkdir(exist_ok=True)

    def _spec_path(self, name: str) -> Path:
        safe_name = "".join(c for c in name if c.isalnum() or c in ("-", "_")).strip()
        if not safe_name:
            safe_name = "unnamed_spec"
        return self.specs_dir / f"{safe_name}.json"

    def save_spec(
        self,
        name: str,
        description: str,
        objective: str,
        criteria: List[str],
        constraints: List[str] = None,
        steps: List[Dict] = None,
    ) -> str:
        """
        Guarda una especificación en disco y registra un índice en Engram.

        Returns:
            str: Nombre de la spec guardada.
        """
        spec = {
            "type": "spec",
            "name": name,
            "description": description,
            "objective": objective,
            "criteria": criteria or [],
            "constraints": constraints or [],
            "steps": steps or [],
            "created_at": datetime.now().isoformat(),
            "status": "draft",  # draft | planned | executing | completed | failed
        }

        path = self._spec_path(name)
        path.write_text(
            json.dumps(spec, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        self.engram.save(
            f"Spec registrada: {name} — {(description or '')[:120]}",
            tags=["spec", f"spec_{name}", "sdd", "planning"],
            source="spec_manager",
            async_mode=False,
        )

        logger.info("Spec guardada en disco: %s", path)
        return name

    def load_spec_by_name(self, name: str) -> Optional[Dict]:
        """Carga una spec por su nombre desde disco."""
        path = self._spec_path(name)
        if not path.exists():
            logger.debug("Spec no encontrada en disco: %s", path)
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("type") == "spec":
                return data
            return None
        except Exception as e:
            logger.exception("Error leyendo spec %s: %s", name, e)
            return None

    def load_spec(self, spec_id: str) -> Optional[Dict]:
        """
        Compatibilidad: intenta cargar por nombre (spec_id se trata como name).
        """
        return self.load_spec_by_name(spec_id)

    def list_specs(self) -> List[Dict]:
        """Lista todas las specs disponibles en disco."""
        specs = []
        for path in sorted(self.specs_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if data.get("type") == "spec":
                    specs.append(
                        {
                            "name": data.get("name"),
                            "description": data.get("description"),
                            "status": data.get("status"),
                            "created_at": data.get("created_at"),
                        }
                    )
            except Exception as e:
                logger.debug("No se pudo leer %s: %s", path, e)
                continue
        return specs

    def update_status(self, name: str, status: str) -> None:
        """Actualiza el estado de una spec en disco."""
        spec = self.load_spec_by_name(name)
        if not spec:
            logger.warning("Spec no encontrada: %s", name)
            return

        spec["status"] = status
        path = self._spec_path(name)
        path.write_text(
            json.dumps(spec, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("Spec %s actualizada a estado: %s", name, status)

    def delete_spec(self, name: str) -> bool:
        """Elimina una spec del disco."""
        path = self._spec_path(name)
        if path.exists():
            path.unlink()
            logger.info("Spec eliminada: %s", name)
            return True
        return False

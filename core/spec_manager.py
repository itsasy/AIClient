import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from core.engram_memory import EngramMemory

logger = logging.getLogger(__name__)


class SpecManager:
    """
    Gestiona especificaciones (Specs) para el flujo SDD.
    Cada Spec es un documento estructurado que se guarda en Engram.
    """

    def __init__(self):
        self.engram = EngramMemory()

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
        Guarda una nueva especificación en Engram.

        Args:
            name: Nombre corto de la spec.
            description: Descripción detallada.
            objective: Objetivo principal.
            criteria: Lista de criterios de éxito.
            constraints: Lista de restricciones (opcional).
            steps: Lista de pasos sugeridos (opcional, se generará automáticamente).

        Returns:
            str: ID de la spec en Engram.
        """
        spec = {
            "type": "spec",
            "name": name,
            "description": description,
            "objective": objective,
            "criteria": criteria,
            "constraints": constraints or [],
            "steps": steps or [],
            "created_at": datetime.now().isoformat(),
            "status": "draft",  # draft, planned, executing, completed, failed
        }
        content = json.dumps(spec, ensure_ascii=False, indent=2)
        self.engram.save(
            content,
            tags=["spec", f"spec_{name}", "sdd", "planning"],
            source="spec_manager",
        )
        # Recuperamos el ID (Engram devuelve True/False, pero no el ID directamente.
        # Para obtenerlo, hacemos una búsqueda por nombre)
        spec_id = self._find_spec_id_by_name(name)
        logger.info("Spec guardada: %s (ID: %s)", name, spec_id)
        return spec_id

    def load_spec(self, spec_id: str) -> Optional[Dict]:
        """Carga una spec por su ID (buscando en Engram)."""
        # Engram no tiene búsqueda por ID directa, así que usamos recall con filtro.
        # Pero podemos buscar por tags: spec_{name}
        # Para simplificar, usamos el nombre en lugar del ID.
        # Mejor: almacenamos el ID en una variable de clase, pero usaremos el enfoque de búsqueda.
        # Vamos a listar todas las specs y buscar por ID en el contenido.
        memories = self.engram.recall("spec", limit=50)
        for m in memories:
            try:
                data = json.loads(m.get("content", "{}"))
                if data.get("type") == "spec" and data.get("id") == spec_id:
                    return data
            except json.JSONDecodeError:
                continue
        return None

    def load_spec_by_name(self, name: str) -> Optional[Dict]:
        """Carga una spec por su nombre."""
        memories = self.engram.recall(f"spec_{name}", limit=10)
        for m in memories:
            try:
                data = json.loads(m.get("content", "{}"))
                if data.get("type") == "spec" and data.get("name") == name:
                    return data
            except json.JSONDecodeError:
                continue
        return None

    def list_specs(self) -> List[Dict]:
        """Lista todas las specs disponibles."""
        memories = self.engram.recall("spec", limit=50)
        specs = []
        for m in memories:
            try:
                data = json.loads(m.get("content", "{}"))
                if data.get("type") == "spec":
                    specs.append(
                        {
                            "name": data.get("name"),
                            "description": data.get("description"),
                            "status": data.get("status"),
                            "created_at": data.get("created_at"),
                        }
                    )
            except json.JSONDecodeError:
                continue
        return specs

    def update_status(self, name: str, status: str):
        """Actualiza el estado de una spec."""
        spec = self.load_spec_by_name(name)
        if not spec:
            logger.warning("Spec no encontrada: %s", name)
            return
        spec["status"] = status
        # Guardar actualizada (sobrescribir)
        self.save_spec(
            name=spec["name"],
            description=spec["description"],
            objective=spec["objective"],
            criteria=spec["criteria"],
            constraints=spec.get("constraints"),
            steps=spec.get("steps"),
        )
        logger.info("Spec %s actualizada a estado: %s", name, status)

    def _find_spec_id_by_name(self, name: str) -> Optional[str]:
        """Busca el ID de una spec por su nombre (usando recall)."""
        memories = self.engram.recall(f"spec_{name}", limit=5)
        for m in memories:
            try:
                data = json.loads(m.get("content", "{}"))
                if data.get("type") == "spec" and data.get("name") == name:
                    # Engram no devuelve ID directamente, pero podemos usar el timestamp como ID
                    return data.get("created_at")
            except json.JSONDecodeError:
                continue
        return None

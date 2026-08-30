import logging
from typing import Any

from core.context.base import BaseContextProvider
from core.execution_plan import ExecutionPlan
from core.discovery.project_importer import ProjectImporter
from core.discovery.template_registry import TemplateRegistry

logger = logging.getLogger(__name__)

class TemplateProvider(BaseContextProvider):
    """
    Inyecta código de UI Templates en el contexto si el plan
    indica que debe usarse uno (por ejemplo, mediante params de un step).
    """
    key = "template"

    def __init__(self) -> None:
        self.registry = TemplateRegistry()
        self.importer = ProjectImporter()

    def load(self, plan: ExecutionPlan, context: dict[str, Any]) -> dict[str, Any]:
        # Para saber qué template usar, buscamos en los parameters de la request o metadata
        template_name = plan.metadata.get("template_name")
        
        if not template_name:
            # Búsqueda implícita en params del coder step si no está en metadatos globales
            for step in plan.steps:
                if step.unit_name in ("coder", "scaffold_ui_shell"):
                    params = getattr(step, "params", {}) or {}
                    template_name = params.get("template") or params.get("variant")
                    if template_name:
                        break

        if not template_name:
            return {}

        template_path = self.registry.get_template(template_name)
        if not template_path:
            logger.warning("Template '%s' solicitado pero no encontrado.", template_name)
            return {}

        logger.info("TemplateProvider cargando template: %s", template_name)
        template_data = self.importer.import_template(template_path)
        
        return template_data

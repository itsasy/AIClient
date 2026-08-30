import logging
from pathlib import Path
from typing import Any

from core.config import Config

logger = logging.getLogger(__name__)

class TemplateRegistry:
    """
    Registro central de UI Templates o semillas de código.
    """
    def __init__(self, templates_dir: Path | None = None) -> None:
        self.templates_dir = templates_dir or (Config.PROJECT_ROOT / "ui_templates")
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self._templates = self._discover()

    def _discover(self) -> dict[str, Path]:
        templates = {}
        for item in self.templates_dir.iterdir():
            if item.is_dir():
                templates[item.name.lower()] = item
        return templates

    def list_templates(self) -> list[str]:
        return list(self._templates.keys())

    def get_template(self, name: str) -> Path | None:
        return self._templates.get(name.lower())

    def refresh(self) -> None:
        self._templates = self._discover()

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from core.config import Config
from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep
from skills.base import Skill


class ScaffoldUiShellSkill(Skill):
    """
    UI shell estático (sin LLM).
    variant=pos|dental|restaurant
    """

    name = "scaffold_ui_shell"
    description = "Copia semillas HTML/CSS de shell operativo al proyecto destino."
    version = "2.0"
    capabilities = ("ui_scaffold", "static_ui", "pos_shell")

    VARIANTS = {
        "pos": "src/ui/pos_shell",
        "dental": "src/ui/dental_shell",
        "restaurant": "src/ui/restaurant_shell",
    }

    def execute(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        params = dict(step.params or {})
        variant = str(params.get("variant") or "pos").strip().lower()
        if variant not in self.VARIANTS:
            variant = "pos"

        force = bool(params.get("force"))
        templates_root = self._resolve_templates_root(variant)
        if templates_root is None:
            return {
                "ok": False,
                "result": None,
                "error": (
                    f"No hay semillas ui_templates/{variant}/. "
                    "Copiá artifacts/ui_templates/{variant} a "
                    "skills/projects/ui_templates/{variant}/ "
                    "(o env UI_TEMPLATES_ROOT)."
                ),
            }

        root = Path(Config.TARGET_PROJECT_ROOT).expanduser().resolve()
        dest = root / self.VARIANTS[variant]
        dest.mkdir(parents=True, exist_ok=True)

        created: list[str] = []
        for path in sorted(templates_root.rglob("*")):
            if not path.is_file():
                continue
            if path.name.upper() == "README.MD" and not force:
                continue
            rel = path.relative_to(templates_root)
            target = dest / rel
            if target.exists() and not force:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            created.append(str(target.relative_to(root)))

        return {
            "ok": True,
            "result": {
                "type": "ui_scaffold",
                "path": self.VARIANTS[variant],
                "variant": variant,
                "created": created,
                "source": str(templates_root),
            },
            "error": None,
        }

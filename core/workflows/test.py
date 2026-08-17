from __future__ import annotations

from typing import Any

from core.commands.workflow import BaseWorkflow
from core.config import Config
from core.execution_plan import ExecutionPlan


class TestWorkflow(BaseWorkflow):
    """
    /test [comando | pos-smoke]

    Sin argumentos: NO ejecuta pytest del AIClient.
    Con argumentos: corre ese comando vía skill shell.

    Atajo:
      /test pos-smoke
        → smoke SaleFacade en TARGET_PROJECT_ROOT
    """

    name = "test"
    description = "Ejecuta un comando de test/smoke. " "Sin args no lanza pytest del orquestador."

    POS_SMOKE_CMD = (
        "cd /tmp && "
        'PYTHONPATH={root} python3 -c "'
        "from src.modules.pos.sale_facade import SaleFacade; "
        "s = SaleFacade(locale='AR'); "
        "s.seed_product('SKU1', 'Café', 15.0); "
        "r = s.sell([('SKU1', 2)]); "
        "print(r['ok'], r['total'], r['payment'].get('status'), "
        "r['invoice'].get('status'), r['cash_balance'], r['estado'])"
        '"'
    )

    def execute(
        self,
        arguments: str,
        context: dict[str, Any] | None = None,
    ) -> ExecutionPlan:
        raw = (arguments or "").strip()

        if not raw:
            cmd = (
                'echo "Uso: /test <comando> | /test pos-smoke. '
                "Default pytest del AIClient desactivado. "
                'Ej: /test pos-smoke"'
            )
            objective = "Mostrar uso de /test (sin pytest por defecto)"
        elif raw.lower() in {"pos-smoke", "pos_smoke", "smoke-pos"}:
            root = Config.TARGET_PROJECT_ROOT.expanduser().resolve()
            cmd = self.POS_SMOKE_CMD.format(root=root)
            objective = f"Smoke SaleFacade en TARGET ({root})"
        else:
            cmd = raw
            objective = f"Ejecutar tests/comando: {cmd}"

        plan = ExecutionPlan(
            original_task=f"/test {raw}".strip() or "/test",
            intent="testing",
            intent_category="testing",
            objective=objective,
            execution_mode="single",
        )
        plan.context_requirements["project"] = False
        plan.governance["allow_shell"] = True
        plan.set_execution_unit(
            unit_type="skill",
            unit_name="shell",
            params={"command": cmd},
        )
        plan.metadata["workflow"] = "test"
        if raw.lower() in {"pos-smoke", "pos_smoke", "smoke-pos"}:
            plan.metadata["smoke"] = "pos_sale_facade"
        return plan

    def validate(self, arguments: str) -> tuple[bool, str]:
        return True, ""

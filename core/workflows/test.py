from __future__ import annotations

from typing import Any

from core.commands.workflow import BaseWorkflow
from core.config import Config
from core.execution_plan import ExecutionPlan


class TestWorkflow(BaseWorkflow):
    """
    /test [product]

    - /test: Ejecuta los tests del orquestador (AIClient).
    - /test product: Ejecuta los tests del producto destino (TARGET_PROJECT_ROOT).
    """

    name = "test"
    description = "Ejecuta los tests del orquestador o del producto."

    def execute(
        self,
        arguments: str,
        context: dict[str, Any] | None = None,
    ) -> ExecutionPlan:
        raw = (arguments or "").strip()

        if raw.lower() in {"product", "--target"}:
            root = Config.TARGET_PROJECT_ROOT.expanduser().resolve()
            objective = f"Run product tests in TARGET ({root})"
        else:
            root = Config.PROJECT_ROOT.expanduser().resolve()
            objective = "Run orchestrator (AIClient) tests"

        from core.discovery.engine import DiscoveryEngine
        discovery = DiscoveryEngine(root)
        env = discovery.discover()

        plan = ExecutionPlan(
            original_task=f"/test {raw}".strip() or "/test",
            intent="testing",
            intent_category="testing",
            objective=objective,
            execution_mode="single",
        )
        plan.metadata["workflow"] = "test"

        test_cmds = env.commands.get("test", [])
        if not test_cmds:
            plan.status = "not_available"
            plan.error = "No test command could be determined from project evidence."
            return plan

        # For simplicity, pick the first high confidence command, or the first one.
        # Discovery separates Candidates vs Execution.
        # In the future, LLM or workflow decides. For now, take the first valid candidate.
        test_cmd = test_cmds[0].value
        cmd = f'cd "{root}" && ' + test_cmd

        plan.context_requirements["project"] = False
        plan.governance["allow_shell"] = True
        plan.set_execution_unit(
            unit_type="skill",
            unit_name="shell",
            params={"command": cmd},
        )
        return plan

    def validate(self, arguments: str) -> tuple[bool, str]:
        return True, ""

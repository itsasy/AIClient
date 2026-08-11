from __future__ import annotations

import logging
from typing import Any

from core.commands.models import CommandResult
from core.commands.workflow import BaseWorkflow
from core.execution_plan import ExecutionPlan

logger = logging.getLogger(__name__)


class CommandRouter:
    """
    Enruta comandos slash a sus workflows correspondientes.

    Flujo:
        User Input → detecta "/comando" → workflow → ExecutionPlan

    Esto evita que el LLM interprete comandos deterministas.
    """

    def __init__(self) -> None:
        self._workflows: dict[str, BaseWorkflow] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Registra los workflows por defecto."""
        # Importamos aquí para evitar dependencias circulares
        from core.workflows.spec import SpecWorkflow
        from core.workflows.plan import PlanWorkflow
        from core.workflows.build import BuildWorkflow
        from core.workflows.test import TestWorkflow
        from core.workflows.review import ReviewWorkflow

        self.register("spec", SpecWorkflow())
        self.register("plan", PlanWorkflow())
        self.register("build", BuildWorkflow())
        self.register("test", TestWorkflow())
        self.register("review", ReviewWorkflow())

    def register(
        self,
        name: str,
        workflow: BaseWorkflow,
    ) -> None:
        """Registra un workflow para un comando."""
        self._workflows[name] = workflow

        logger.info(
            "Workflow registrado: /%s",
            name,
        )

    def list_commands(self) -> list[str]:
        """
        Devuelve los comandos registrados.

        La implementación interna de los workflows permanece
        encapsulada dentro de CommandRouter.
        """
        return sorted(self._workflows.keys())

    def route(
        self,
        user_input: str,
    ) -> CommandResult | None:
        """
        Analiza la entrada y devuelve un CommandResult
        si es un comando slash.
        """
        if not user_input or not user_input.strip():
            return None

        stripped = user_input.strip()

        if not stripped.startswith("/"):
            return None

        # Extraer comando y argumentos
        parts = stripped[1:].split(maxsplit=1)
        command = parts[0].lower().strip()
        arguments = parts[1] if len(parts) > 1 else ""

        if not command:
            return None

        return CommandResult(
            command=command,
            arguments=arguments,
        )

    def execute(
        self,
        command: str,
        arguments: str,
        context: dict[str, Any] | None = None,
    ) -> ExecutionPlan | None:
        """
        Ejecuta el workflow correspondiente al comando.
        """
        workflow = self._workflows.get(command)

        if workflow is None:
            logger.warning(
                "Comando desconocido: /%s",
                command,
            )
            return None

        # Validar argumentos
        valid, error = workflow.validate(arguments)

        if not valid:
            raise ValueError(f"Argumentos inválidos para /{command}: {error}")

        # Ejecutar workflow
        return workflow.execute(
            arguments,
            context,
        )

    def process(
        self,
        user_input: str,
        context: dict[str, Any] | None = None,
    ) -> ExecutionPlan | None:
        """
        Procesa la entrada completa: si es comando slash,
        devuelve ExecutionPlan.

        Si no es comando slash, devuelve None
        y la entrada debe continuar con IntentAnalyzer.
        """
        result = self.route(user_input)

        if result is None:
            return None

        return self.execute(
            result.command,
            result.arguments,
            context,
        )

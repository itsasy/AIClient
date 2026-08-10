from __future__ import annotations

from core.execution_plan import ExecutionPlan
from core.intent import IntentResult
from .execution_planner import ExecutionPlanner


class PlanBuilder:
    """
    Construye ExecutionPlans a partir de IntentResult.

    Responsabilidades:

    - Recibir un IntentResult válido.
    - Delegar la construcción al ExecutionPlanner.
    - Enriquecer el plan con información del IntentResult.
    - Validar el ExecutionPlan resultante.

    No:

    - analiza lenguaje natural;
    - ejecuta agentes;
    - ejecuta skills;
    - gestiona contexto;
    - gestiona lifecycle de ejecución.
    """

    name = "plan_builder"

    def __init__(
        self,
        planner: type[ExecutionPlanner] = ExecutionPlanner,
    ) -> None:
        self.planner = planner

    # =========================================================
    # Public API
    # =========================================================

    def build(
        self,
        intent: IntentResult,
        original_task: str,
    ) -> ExecutionPlan:
        if not isinstance(
            intent,
            IntentResult,
        ):
            raise TypeError("PlanBuilder requiere un IntentResult.")

        if not original_task or not original_task.strip():
            raise ValueError("PlanBuilder requiere una tarea original.")

        task = original_task.strip()

        plan = self.planner.create(
            task=task,
            intent=intent,
        )

        self._enrich_plan(
            plan,
            intent,
        )

        errors = plan.validate()

        if errors:
            raise ValueError("ExecutionPlan inválido: " + ", ".join(errors))

        return plan

    def build_from_dict(
        self,
        intent_data: dict,
        original_task: str,
    ) -> ExecutionPlan:
        """
        Adaptador de compatibilidad.

        La API principal sigue siendo build(IntentResult, ...).
        """

        if not isinstance(
            intent_data,
            dict,
        ):
            raise TypeError("intent_data debe ser un diccionario.")

        intent = IntentResult.from_dict(
            {
                **intent_data,
                "original_query": original_task,
            }
        )

        return self.build(
            intent,
            original_task,
        )

    # =========================================================
    # Enrichment
    # =========================================================

    def _enrich_plan(
        self,
        plan: ExecutionPlan,
        intent: IntentResult,
    ) -> None:
        """
        Agrega información semántica del IntentResult al plan.

        El plan conserva su propio contrato de ejecución.
        """

        plan.metadata.update(
            {
                "builder": self.name,
                "intent_result": intent.to_dict(),
                "intent_confidence": intent.confidence,
                "intent_category": intent.category,
                "intent_signals": list(intent.signals),
            }
        )

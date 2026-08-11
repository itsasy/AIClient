from __future__ import annotations

from typing import Any

from core.execution_plan import ExecutionPlan
from core.intent import IntentResult
from core.planning.execution_planner import ExecutionPlanner


class PlanBuilder:
    """
    Construye ExecutionPlans a partir de IntentResult.

    PlanBuilder actúa como frontera entre la interpretación semántica
    y la planificación ejecutable.

    Responsabilidades:

        - Recibir un IntentResult válido.
        - Delegar la construcción del ExecutionPlan al ExecutionPlanner.
        - Preservar metadata relevante de la intención.
        - Validar el ExecutionPlan resultante.

    No:

        - Analiza lenguaje natural.
        - Selecciona Agents.
        - Selecciona Skills.
        - Ejecuta Agents.
        - Ejecuta Skills.
        - Gestiona contexto.
        - Ejecuta herramientas.
        - Gestiona lifecycle de ejecución.
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
        """
        Construye y valida un ExecutionPlan.

        Flujo:

            IntentResult
                ↓
            ExecutionPlanner
                ↓
            ExecutionPlan
                ↓
            Validation
        """

        if not isinstance(intent, IntentResult):
            raise TypeError("PlanBuilder requiere una instancia válida de IntentResult.")

        if not isinstance(original_task, str):
            raise TypeError("PlanBuilder.original_task debe ser un string.")

        original_task = original_task.strip()

        if not original_task:
            raise ValueError("PlanBuilder requiere una tarea original.")

        intent_data = intent.to_dict()

        plan = self.planner.create(
            task=original_task,
            intent=intent_data,
        )

        self._attach_metadata(
            plan=plan,
            intent=intent,
            original_task=original_task,
        )

        errors = plan.validate()

        if errors:
            raise ValueError("ExecutionPlan inválido: " + ", ".join(errors))

        return plan

    # =========================================================
    # Metadata
    # =========================================================

    @classmethod
    def _attach_metadata(
        cls,
        plan: ExecutionPlan,
        intent: IntentResult,
        original_task: str,
    ) -> None:
        """
        Adjunta información de trazabilidad al ExecutionPlan.

        La metadata no modifica la semántica ni la estrategia
        de ejecución del plan.
        """

        intent_data = intent.to_dict()

        plan.metadata.update(
            {
                "builder": cls.name,
                "intent_result": intent_data,
                "intent_confidence": intent.confidence,
                "intent_category": intent.category,
                "intent_domain": intent.domain,
                "intent_complexity": intent.complexity,
                "intent_signals": list(intent.signals),
                "original_task": original_task,
            }
        )

        # Preservar metadata producida por IntentAnalyzer,
        # sin sobrescribir información existente del plan.
        if intent.metadata:
            plan.metadata.setdefault(
                "intent_metadata",
                {},
            )

            if isinstance(plan.metadata["intent_metadata"], dict):
                plan.metadata["intent_metadata"].update(intent.metadata)

    # =========================================================
    # Convenience
    # =========================================================

    def build_from_dict(
        self,
        intent_data: dict[str, Any],
        original_task: str,
    ) -> ExecutionPlan:
        """
        Construye un ExecutionPlan a partir de un diccionario
        serializado de intención.

        Útil para integraciones externas, tests y persistencia.
        """

        if not isinstance(intent_data, dict):
            raise TypeError("intent_data debe ser un diccionario.")

        if not isinstance(original_task, str):
            raise TypeError("original_task debe ser un string.")

        intent = IntentResult(
            intent=intent_data.get(
                "intent",
                "conversation",
            ),
            domain=intent_data.get(
                "domain",
                "general",
            ),
            category=intent_data.get(
                "category",
                "general",
            ),
            complexity=intent_data.get(
                "complexity",
                "normal",
            ),
            confidence=intent_data.get(
                "confidence",
                0.0,
            ),
            entities=intent_data.get(
                "entities",
                {},
            ),
            signals=intent_data.get(
                "signals",
                [],
            ),
            original_query=str(
                intent_data.get("original_query") or original_task or "",
            ),
            metadata=intent_data.get(
                "metadata",
                {},
            ),
        )

        return self.build(
            intent=intent,
            original_task=original_task,
        )

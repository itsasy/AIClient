from __future__ import annotations

from core.intent import IntentResult
from core.execution_plan import ExecutionPlan
from core.planning.execution_planner import ExecutionPlanner


class PlanBuilder:
    """
    Construye ExecutionPlans a partir de IntentResult.
    """

    name = "plan_builder"

    def __init__(self, planner: type[ExecutionPlanner] = ExecutionPlanner):
        self.planner = planner

    def build(self, intent: IntentResult, original_task: str) -> ExecutionPlan:
        if not original_task or not original_task.strip():
            raise ValueError("PlanBuilder requiere una tarea original.")

        if not intent:
            raise ValueError("PlanBuilder requiere IntentResult.")

        plan = self.planner.create(
            task=original_task,
            intent=intent.to_dict(),
        )

        plan.metadata.update(
            {
                "builder": PlanBuilder.name,
                "intent_result": intent.to_dict(),
                "intent_confidence": intent.confidence,
                "intent_category": intent.category,
                "intent_signals": list(intent.signals),
            }
        )

        errors = plan.validate()
        if errors:
            raise ValueError("ExecutionPlan inválido: " + ", ".join(errors))

        return plan

    def build_from_dict(self, intent_data: dict, original_task: str) -> ExecutionPlan:
        intent = IntentResult(
            intent=intent_data.get("intent", "conversation"),
            domain=intent_data.get("domain", "general"),
            category=intent_data.get("category", "general"),
            complexity=intent_data.get("complexity", "normal"),
            confidence=intent_data.get("confidence", 0.0),
            entities=intent_data.get("entities", {}),
            signals=intent_data.get("signals", []),
            original_query=original_task,
            metadata=intent_data.get("metadata", {}),
        )
        return self.build(intent, original_task)

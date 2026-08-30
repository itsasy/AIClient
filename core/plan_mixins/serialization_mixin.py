from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from core.execution_step import ExecutionStep

class PlanSerializationMixin:
    def to_dict(
        self,
        include_runtime: bool = True,
        include_step_results: bool = True,
    ) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "status": self.status,
            "original_task": self.original_task,
            "intent": self.intent,
            "intent_category": self.intent_category,
            "objective": self.objective,
            "execution_mode": self.execution_mode,
            "execution_unit_type": self.execution_unit_type,
            "execution_unit": self.execution_unit,
            "params": dict(self.params),
            "constraints": list(self.constraints),
            "context_requirements": dict(self.context_requirements),
            "governance": dict(self.governance),
            "execution_policy": dict(self.execution_policy),
            "metadata": dict(self.metadata),
            "steps": [step.to_dict() for step in self.steps],
        }

        if include_step_results:
            data["steps"] = [step.to_dict() for step in self.steps]
        else:
            data["steps"] = [
                {
                    "id": step.id,
                    "description": step.description,
                    "unit_type": step.unit_type,
                    "unit_name": step.unit_name,
                    "params": dict(step.params),
                    "depends_on": list(step.depends_on),
                    "expected_output": step.expected_output,
                    "max_retries": step.max_retries,
                    "retry_count": step.retry_count,
                    "timeout": step.timeout,
                    "status": step.status,
                    "metadata": dict(step.metadata),
                }
                for step in self.steps
            ]

        if include_runtime:
            data["loaded_context"] = dict(self.loaded_context)
            data["execution_context"] = dict(self.execution_context)
            data["result"] = self.result
            data["error"] = self.error

        return data

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> ExecutionPlan:
        if not isinstance(data, dict):
            raise ValueError("ExecutionPlan.from_dict requiere " "un diccionario.")

        created_at_value = data.get("created_at")

        if created_at_value:
            try:
                created_at = datetime.fromisoformat(created_at_value)
            except (
                TypeError,
                ValueError,
            ) as exc:
                raise ValueError("ExecutionPlan.created_at inválido.") from exc
        else:
            created_at = datetime.now(timezone.utc)

        raw_steps = data.get(
            "steps",
            [],
        )

        if not isinstance(
            raw_steps,
            list,
        ):
            raise ValueError("ExecutionPlan.steps debe ser una lista.")

        steps = [ExecutionStep.from_dict(step) for step in raw_steps]

        raw_params = data.get(
            "params",
            {},
        )

        raw_constraints = data.get(
            "constraints",
            [],
        )

        raw_context = data.get(
            "context_requirements",
            cls.DEFAULT_CONTEXT_REQUIREMENTS,
        )

        raw_governance = data.get(
            "governance",
            cls.DEFAULT_GOVERNANCE,
        )

        raw_policy = data.get(
            "execution_policy",
            cls.DEFAULT_EXECUTION_POLICY,
        )

        raw_loaded_context = data.get(
            "loaded_context",
            {},
        )

        raw_execution_context = data.get(
            "execution_context",
            {},
        )

        raw_metadata = data.get(
            "metadata",
            {},
        )

        if not isinstance(
            raw_params,
            dict,
        ):
            raise ValueError("ExecutionPlan.params debe ser " "un diccionario.")

        if not isinstance(
            raw_constraints,
            list,
        ):
            raise ValueError("ExecutionPlan.constraints debe ser " "una lista.")

        if not isinstance(
            raw_context,
            dict,
        ):
            raise ValueError("ExecutionPlan.context_requirements " "debe ser un diccionario.")

        if not isinstance(
            raw_governance,
            dict,
        ):
            raise ValueError("ExecutionPlan.governance debe ser " "un diccionario.")

        if not isinstance(
            raw_policy,
            dict,
        ):
            raise ValueError("ExecutionPlan.execution_policy debe " "ser un diccionario.")

        if not isinstance(
            raw_loaded_context,
            dict,
        ):
            raise ValueError("ExecutionPlan.loaded_context debe " "ser un diccionario.")

        if not isinstance(
            raw_execution_context,
            dict,
        ):
            raise ValueError("ExecutionPlan.execution_context debe " "ser un diccionario.")

        if not isinstance(
            raw_metadata,
            dict,
        ):
            raise ValueError("ExecutionPlan.metadata debe ser " "un diccionario.")

        return cls(
            id=data.get(
                "id",
                str(uuid.uuid4()),
            ),
            created_at=created_at,
            status=data.get(
                "status",
                "pending",
            ),
            original_task=data.get(
                "original_task",
                "",
            ),
            intent=data.get("intent"),
            intent_category=data.get("intent_category"),
            objective=data.get("objective"),
            execution_mode=data.get(
                "execution_mode",
                "single",
            ),
            execution_unit_type=data.get("execution_unit_type"),
            execution_unit=data.get("execution_unit"),
            params=dict(raw_params),
            constraints=list(raw_constraints),
            context_requirements=dict(raw_context),
            governance=dict(raw_governance),
            execution_policy=dict(raw_policy),
            steps=steps,
            loaded_context=dict(raw_loaded_context),
            execution_context=dict(raw_execution_context),
            result=data.get("result"),
            error=data.get("error"),
            metadata=dict(raw_metadata),
        )


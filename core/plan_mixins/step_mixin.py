from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from core.execution_step import ExecutionStep

class PlanStepMixin:
    def set_execution_unit(
        self,
        unit_type: str,
        unit_name: str,
        params: dict[str, Any] | None = None,
    ) -> None:
        """
        Define la unidad ejecutable de un plan single.
        """

        if not self.is_single():
            raise ValueError(
                "set_execution_unit solo puede utilizarse " "en un ExecutionPlan single."
            )

        normalized_type = self.normalize_unit_type(unit_type)

        if normalized_type is None:
            raise ValueError("unit_type no puede ser None.")

        if not isinstance(unit_name, str):
            raise ValueError("unit_name debe ser un string.")

        unit_name = unit_name.strip()

        if not unit_name:
            raise ValueError("unit_name no puede estar vacío.")

        if params is None:
            params = {}

        if not isinstance(params, dict):
            raise TypeError("params debe ser un diccionario.")

        self.execution_unit_type = normalized_type
        self.execution_unit = unit_name
        self.params = dict(params)

    def clear_execution_unit(self) -> None:
        self.execution_unit_type = None
        self.execution_unit = None
        self.params.clear()

    def uses_unit(
        self,
        unit_type: str,
        unit_name: str,
    ) -> bool:
        normalized_type = self.normalize_unit_type(unit_type)

        if normalized_type is None:
            return False

        unit_name = unit_name.strip()

        if self.execution_unit_type == normalized_type and self.execution_unit == unit_name:
            return True

        return any(
            step.unit_type == normalized_type and step.unit_name == unit_name for step in self.steps
        )

    def add_step(
        self,
        step: ExecutionStep | None = None,
        *,
        description: str | None = None,
        unit_type: str | None = None,
        unit_name: str | None = None,
        params: dict | None = None,
        expected_output: str | None = None,
        depends_on: list[str] | None = None,
        metadata: dict | None = None,
        max_retries: int = 0,
        timeout: int = 120,
    ) -> ExecutionStep:
        """
        Añade un step al plan.

        Formas soportadas:
        1) plan.add_step(execution_step_instance)
        2) plan.add_step(description=..., unit_type=..., unit_name=..., ...)
        """
        from core.execution_step import ExecutionStep

        if step is not None:
            if not isinstance(step, ExecutionStep):
                raise TypeError("step debe ser una instancia de ExecutionStep")
            if any(s.id == step.id for s in self.steps):
                raise ValueError(f"Ya existe un step con id={step.id}")
            self.steps.append(step)
            return step

        if not description or not unit_type or not unit_name:
            raise ValueError(
                "Si no pasas un ExecutionStep, debes indicar " "description, unit_type y unit_name"
            )

        new_step = ExecutionStep(
            description=description,
            unit_type=unit_type,
            unit_name=unit_name,
            params=dict(params or {}),
            expected_output=expected_output,
            depends_on=list(depends_on or []),
            metadata=dict(metadata or {}),
            max_retries=max_retries,
            timeout=timeout,
        )

        if any(s.id == new_step.id for s in self.steps):
            raise ValueError(f"Ya existe un step con id={new_step.id}")

        self.steps.append(new_step)
        return new_step

    def remove_step(self, step_id: str) -> bool:
        for i, step in enumerate(self.steps):
            if step.id == step_id:
                self.steps.pop(i)
                return True
        return False

    def get_step(self, step_id: str) -> ExecutionStep | None:
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

    def has_steps(self) -> bool:
        return bool(self.steps)

    def is_multi_step(self) -> bool:
        return self.execution_mode == "multi_step"

    def is_single(self) -> bool:
        return self.execution_mode == "single"

    def dependencies_for(self, step: ExecutionStep) -> list[ExecutionStep]:
        deps = []
        for dep_id in step.depends_on:
            found = self.get_step(dep_id)
            if found:
                deps.append(found)
        return deps


from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from core.execution_step import ExecutionStep

class PlanValidationMixin:
    def validate(self) -> list[str]:
        errors: list[str] = []

        if not self.original_task:
            errors.append("ExecutionPlan requiere original_task.")

        if not self.intent:
            errors.append("ExecutionPlan requiere intent.")

        if not self.objective:
            errors.append("ExecutionPlan requiere objective.")

        if self.execution_mode == "single":
            if not self.execution_unit_type:
                errors.append("Modo single requiere " "execution_unit_type.")

            if not self.execution_unit:
                errors.append("Modo single requiere " "execution_unit.")

            if self.steps:
                errors.append("Modo single no permite steps.")

        elif self.execution_mode == "multi_step":
            if self.execution_unit_type or self.execution_unit:
                errors.append("Modo multi_step no puede definir " "una unidad ejecutable directa.")

            if not self.steps:
                errors.append("Modo multi_step requiere al menos " "un step.")

        errors.extend(self.validate_dependencies())

        if self.has_dependency_cycle():
            errors.append("ExecutionPlan contiene un ciclo " "de dependencias.")

        for index, step in enumerate(
            self.steps,
            start=1,
        ):
            if not step.description.strip():
                errors.append(f"Step {index} requiere descripción.")

            if not step.unit_type:
                errors.append(f"Step {index} requiere unit_type.")

            if not step.unit_name:
                errors.append(f"Step {index} requiere unit_name.")

        if self.governance.get(
            "allow_sudo",
            False,
        ):
            if not self.governance.get(
                "allow_shell",
                False,
            ):
                errors.append("allow_sudo requiere allow_shell.")

        return errors

    def is_valid(self) -> bool:
        return not self.validate()

    def validate_dependencies(self) -> list[str]:
        errors: list[str] = []

        step_ids = [step.id for step in self.steps]

        step_id_set = set(step_ids)

        if len(step_ids) != len(step_id_set):
            errors.append("ExecutionPlan contiene IDs de steps duplicados.")

        for step in self.steps:
            for dependency in step.depends_on:
                if dependency == step.id:
                    errors.append(f"Step {step.id} depende de sí mismo.")
                    continue

                if dependency not in step_id_set:
                    errors.append(f"Step {step.id} depende de " f"{dependency}, que no existe.")

        return errors

    def has_dependency_cycle(self) -> bool:
        graph = {step.id: list(step.depends_on) for step in self.steps}

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(
            node: str,
        ) -> bool:
            if node in visiting:
                return True

            if node in visited:
                return False

            visiting.add(node)

            for dependency in graph.get(
                node,
                [],
            ):
                if dependency in graph and visit(dependency):
                    return True

            visiting.remove(node)
            visited.add(node)

            return False

        return any(visit(step_id) for step_id in graph)

    def _validate_containers(self) -> None:
        containers = {
            "params": self.params,
            "context_requirements": self.context_requirements,
            "governance": self.governance,
            "execution_policy": self.execution_policy,
            "loaded_context": self.loaded_context,
            "execution_context": self.execution_context,
            "metadata": self.metadata,
        }

        for name, value in containers.items():
            if not isinstance(value, dict):
                raise ValueError(f"ExecutionPlan.{name} debe ser un diccionario.")

        if not isinstance(self.constraints, list):
            raise ValueError("ExecutionPlan.constraints debe ser una lista.")

        if not isinstance(self.steps, list):
            raise ValueError("ExecutionPlan.steps debe ser una lista.")

        for step in self.steps:
            if not isinstance(step, ExecutionStep):
                raise ValueError("ExecutionPlan.steps solo puede contener " "ExecutionStep.")


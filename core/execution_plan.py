from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import uuid

from core.execution_step import ExecutionStep


@dataclass(slots=True)
class ExecutionPlan:
    """
    Contrato central de ejecución de AIClient.

    ExecutionPlan representa QUÉ debe ejecutarse y bajo qué
    condiciones.

    Es la fuente de verdad entre Planning y Runtime.

    Flujo:

        IntentResult
            ↓
        ExecutionPlanner
            ↓
        ExecutionPlan
            ↓
        Runtime
            ↓
        ExecutionStep

    ExecutionPlan no ejecuta agentes ni skills.
    """

    VALID_EXECUTION_MODES = frozenset(
        {
            "single",
            "multi_step",
        }
    )

    VALID_STATUSES = frozenset(
        {
            "pending",
            "planned",
            "validated",
            "running",
            "completed",
            "partial",
            "failed",
            "cancelled",
        }
    )

    VALID_UNIT_TYPES = ExecutionStep.VALID_UNIT_TYPES

    VALID_GOVERNANCE_MODES = frozenset(
        {
            "safe",
            "powerful",
        }
    )

    DEFAULT_CONTEXT_REQUIREMENTS = {
        "project": False,
        "engram": False,
        "obsidian": False,
        "gentleman": False,
        "standards": False,
        "documents": False,
        "memory": False,
        "spec": False,
        "swarmforge": False,
    }

    DEFAULT_GOVERNANCE = {
        "mode": "safe",
        "allow_shell": False,
        "allow_network": False,
        "allow_write": False,
        "allow_sudo": False,
    }

    DEFAULT_EXECUTION_POLICY = {
        "autonomous": False,
        "max_retries": 2,
        "requires_approval": False,
        "stop_on_error": True,
        "timeout": 300,
    }

    # =========================================================
    # Identity
    # =========================================================

    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    status: str = "pending"

    # =========================================================
    # Intent
    # =========================================================

    original_task: str = ""

    intent: str | None = None

    intent_category: str | None = None

    objective: str | None = None

    # =========================================================
    # Execution
    # =========================================================

    execution_mode: str = "single"

    execution_unit_type: str | None = None

    execution_unit: str | None = None

    # =========================================================
    # Parameters
    # =========================================================

    params: dict[str, Any] = field(default_factory=dict)

    constraints: list[str] = field(default_factory=list)

    # =========================================================
    # Context requirements
    # =========================================================

    context_requirements: dict[str, bool] = field(
        default_factory=lambda: dict(ExecutionPlan.DEFAULT_CONTEXT_REQUIREMENTS)
    )

    # =========================================================
    # Governance
    # =========================================================

    governance: dict[str, Any] = field(
        default_factory=lambda: dict(ExecutionPlan.DEFAULT_GOVERNANCE)
    )

    # =========================================================
    # Execution policy
    # =========================================================

    execution_policy: dict[str, Any] = field(
        default_factory=lambda: dict(ExecutionPlan.DEFAULT_EXECUTION_POLICY)
    )

    # =========================================================
    # Steps
    # =========================================================

    steps: list[ExecutionStep] = field(default_factory=list)

    # =========================================================
    # Runtime context
    # =========================================================

    loaded_context: dict[str, Any] = field(default_factory=dict)

    execution_context: dict[str, Any] = field(default_factory=dict)

    # =========================================================
    # Metadata
    # =========================================================

    metadata: dict[str, Any] = field(default_factory=dict)

    # =========================================================
    # Lifecycle
    # =========================================================

    def __post_init__(self) -> None:
        self.original_task = self._normalize_text(self.original_task)

        self.execution_mode = self.normalize_execution_mode(self.execution_mode)

        self.status = self.normalize_status(self.status)

        if self.execution_unit_type is not None:
            self.execution_unit_type = self.normalize_unit_type(self.execution_unit_type)

        if self.execution_unit is not None:
            self.execution_unit = self.execution_unit.strip()

            if not self.execution_unit:
                self.execution_unit = None

        self.intent = self._normalize_optional_text(self.intent)

        self.intent_category = self._normalize_optional_text(self.intent_category)

        self.objective = self._normalize_optional_text(self.objective)

        self._validate_containers()
        self._normalize_context_requirements()
        self._normalize_governance()
        self._normalize_execution_policy()

    # =========================================================
    # Normalization
    # =========================================================

    @staticmethod
    def _normalize_text(value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("El valor debe ser un string.")

        return value.strip()

    @staticmethod
    def _normalize_optional_text(
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        if not isinstance(value, str):
            raise ValueError("El valor debe ser un string o None.")

        value = value.strip()

        return value or None

    @classmethod
    def normalize_unit_type(
        cls,
        unit_type: str | None,
    ) -> str | None:
        if unit_type is None:
            return None

        if not isinstance(unit_type, str):
            raise ValueError("execution_unit_type debe ser un string o None.")

        value = unit_type.lower().strip().replace("-", "_").replace(" ", "_")

        if value not in cls.VALID_UNIT_TYPES:
            raise ValueError(
                f"Tipo de unidad inválido: {value}. "
                "Tipos permitidos: "
                f"{sorted(cls.VALID_UNIT_TYPES)}"
            )

        return value

    @classmethod
    def normalize_execution_mode(
        cls,
        mode: str | None,
    ) -> str:
        if mode is None:
            return "single"

        if not isinstance(mode, str):
            raise ValueError("execution_mode debe ser un string.")

        value = mode.lower().strip().replace("-", "_").replace(" ", "_")

        if value not in cls.VALID_EXECUTION_MODES:
            raise ValueError(
                f"Modo de ejecución inválido: {value}. "
                "Modos permitidos: "
                f"{sorted(cls.VALID_EXECUTION_MODES)}"
            )

        return value

    @classmethod
    def normalize_status(
        cls,
        status: str,
    ) -> str:
        if not isinstance(status, str):
            raise ValueError("ExecutionPlan.status debe ser un string.")

        value = status.lower().strip()

        if value not in cls.VALID_STATUSES:
            raise ValueError(
                f"Estado de plan inválido: {value}. "
                "Estados permitidos: "
                f"{sorted(cls.VALID_STATUSES)}"
            )

        return value

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

    # =========================================================
    # Context
    # =========================================================

    def _normalize_context_requirements(self) -> None:
        for provider, required in list(self.context_requirements.items()):
            if not isinstance(provider, str):
                raise ValueError("Los nombres de providers de contexto " "deben ser strings.")

            normalized_provider = provider.lower().strip()

            if not normalized_provider:
                raise ValueError("El nombre del provider de contexto " "no puede estar vacío.")

            if not isinstance(required, bool):
                raise ValueError(f"context_requirements.{provider} " "debe ser booleano.")

            if normalized_provider != provider:
                del self.context_requirements[provider]

            self.context_requirements[normalized_provider] = required

    def requires_context(
        self,
        provider: str,
    ) -> bool:
        if not provider:
            return False

        return bool(
            self.context_requirements.get(
                provider.lower().strip(),
                False,
            )
        )

    def set_context_requirement(
        self,
        provider: str,
        required: bool,
    ) -> None:
        if not provider or not provider.strip():
            raise ValueError("El provider de contexto no puede estar vacío.")

        if not isinstance(required, bool):
            raise ValueError("required debe ser booleano.")

        self.context_requirements[provider.lower().strip()] = required

    # =========================================================
    # Governance
    # =========================================================

    def _normalize_governance(self) -> None:
        mode = (
            str(
                self.governance.get(
                    "mode",
                    "safe",
                )
            )
            .lower()
            .strip()
        )

        if mode not in self.VALID_GOVERNANCE_MODES:
            raise ValueError(
                f"Modo de governance inválido: {mode}. "
                "Modos permitidos: "
                f"{sorted(self.VALID_GOVERNANCE_MODES)}"
            )

        self.governance["mode"] = mode

        for key in (
            "allow_shell",
            "allow_network",
            "allow_write",
            "allow_sudo",
        ):
            value = self.governance.get(
                key,
                False,
            )

            if not isinstance(value, bool):
                raise ValueError(f"governance.{key} debe ser booleano.")

            self.governance[key] = value

    def is_safe_mode(self) -> bool:
        return (
            self.governance.get(
                "mode",
                "safe",
            )
            == "safe"
        )

    def is_powerful_mode(self) -> bool:
        return (
            self.governance.get(
                "mode",
                "safe",
            )
            == "powerful"
        )

    def allows_shell(self) -> bool:
        return bool(
            self.governance.get(
                "allow_shell",
                False,
            )
        )

    def allows_network(self) -> bool:
        return bool(
            self.governance.get(
                "allow_network",
                False,
            )
        )

    def allows_write(self) -> bool:
        return bool(
            self.governance.get(
                "allow_write",
                False,
            )
        )

    def allows_sudo(self) -> bool:
        return bool(
            self.governance.get(
                "allow_sudo",
                False,
            )
        )

    # =========================================================
    # Execution policy
    # =========================================================

    def _normalize_execution_policy(self) -> None:
        autonomous = self.execution_policy.get(
            "autonomous",
            False,
        )

        if not isinstance(autonomous, bool):
            raise ValueError("execution_policy.autonomous debe ser booleano.")

        self.execution_policy["autonomous"] = autonomous

        max_retries = self.execution_policy.get(
            "max_retries",
            2,
        )

        if not isinstance(max_retries, int) or max_retries < 0:
            raise ValueError(
                "execution_policy.max_retries debe ser " "un entero mayor o igual a cero."
            )

        self.execution_policy["max_retries"] = max_retries

        requires_approval = self.execution_policy.get(
            "requires_approval",
            False,
        )

        if not isinstance(requires_approval, bool):
            raise ValueError("execution_policy.requires_approval debe " "ser booleano.")

        self.execution_policy["requires_approval"] = requires_approval

        stop_on_error = self.execution_policy.get(
            "stop_on_error",
            True,
        )

        if not isinstance(stop_on_error, bool):
            raise ValueError("execution_policy.stop_on_error debe ser booleano.")

        self.execution_policy["stop_on_error"] = stop_on_error

        timeout = self.execution_policy.get(
            "timeout",
            300,
        )

        if not isinstance(timeout, int) or timeout <= 0:
            raise ValueError("execution_policy.timeout debe ser " "un entero mayor que cero.")

        self.execution_policy["timeout"] = timeout

    def is_autonomous(self) -> bool:
        return bool(
            self.execution_policy.get(
                "autonomous",
                False,
            )
        )

    def get_max_retries(self) -> int:
        return int(
            self.execution_policy.get(
                "max_retries",
                2,
            )
        )

    def requires_approval(self) -> bool:
        return bool(
            self.execution_policy.get(
                "requires_approval",
                False,
            )
        )

    def should_stop_on_error(self) -> bool:
        return bool(
            self.execution_policy.get(
                "stop_on_error",
                True,
            )
        )

    def get_timeout(self) -> int:
        return int(
            self.execution_policy.get(
                "timeout",
                300,
            )
        )

    # =========================================================
    # Execution unit
    # =========================================================

    def set_execution_unit(
        self,
        unit_type: str,
        unit_name: str,
        params: dict[str, Any] | None = None,
    ) -> None:
        """
        Define la unidad ejecutable de un plan single.

        En modo single la unidad vive directamente en el plan
        y no se representa como ExecutionStep.
        """

        normalized_type = self.normalize_unit_type(unit_type)

        if normalized_type is None:
            raise ValueError("unit_type no puede ser None.")

        if not unit_name or not unit_name.strip():
            raise ValueError("unit_name no puede estar vacío.")

        if params is None:
            params = {}

        if not isinstance(params, dict):
            raise TypeError("params debe ser un diccionario.")

        self.execution_unit_type = normalized_type
        self.execution_unit = unit_name.strip()
        self.params = dict(params)

    def clear_execution_unit(self) -> None:
        self.execution_unit_type = None
        self.execution_unit = None
        self.params.clear()

    # =========================================================
    # Steps
    # =========================================================

    def add_step(
        self,
        description: str,
        unit_type: str,
        unit_name: str,
        params: dict[str, Any] | None = None,
        expected_output: str | None = None,
        retries: int = 0,
        timeout: int = 120,
        metadata: dict[str, Any] | None = None,
    ) -> ExecutionStep:
        if self.execution_mode == "single":
            raise ValueError("No se pueden agregar steps a un " "ExecutionPlan en modo single.")

        normalized_unit_type = self.normalize_unit_type(unit_type)

        if normalized_unit_type is None:
            raise ValueError("unit_type no puede ser None.")

        if not unit_name or not unit_name.strip():
            raise ValueError("unit_name no puede estar vacío.")

        if params is None:
            params = {}

        if not isinstance(params, dict):
            raise TypeError("params debe ser un diccionario.")

        if metadata is None:
            metadata = {}

        if not isinstance(metadata, dict):
            raise TypeError("metadata debe ser un diccionario.")

        step = ExecutionStep(
            description=description,
            unit_type=normalized_unit_type,
            unit_name=unit_name,
            params=dict(params),
            expected_output=expected_output,
            retries=retries,
            timeout=timeout,
            metadata=dict(metadata),
        )

        self.steps.append(step)

        return step

    def remove_step(
        self,
        step_id: str,
    ) -> bool:
        for index, step in enumerate(self.steps):
            if step.id == step_id:
                self.steps.pop(index)

                for remaining in self.steps:
                    remaining.remove_dependency(step_id)

                return True

        return False

    def get_step(
        self,
        step_id: str,
    ) -> ExecutionStep | None:
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

    # =========================================================
    # Dependency graph
    # =========================================================

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

        def visit(node: str) -> bool:
            if node in visiting:
                return True

            if node in visited:
                return False

            visiting.add(node)

            for dependency in graph.get(node, []):
                if dependency in graph and visit(dependency):
                    return True

            visiting.remove(node)
            visited.add(node)

            return False

        return any(visit(step_id) for step_id in graph)

    # =========================================================
    # Validation
    # =========================================================

    def validate(self) -> list[str]:
        errors: list[str] = []

        if not self.original_task:
            errors.append("ExecutionPlan requiere original_task.")

        if not self.intent:
            errors.append("ExecutionPlan requiere intent.")

        if self.execution_mode == "single":
            if not self.execution_unit_type:
                errors.append("Modo single requiere execution_unit_type.")

            if not self.execution_unit:
                errors.append("Modo single requiere execution_unit.")

            if self.steps:
                errors.append("Modo single no permite steps.")

        elif self.execution_mode == "multi_step":
            if not self.steps and not self.execution_unit:
                errors.append(
                    "Modo multi_step requiere al menos " "un step o una unidad ejecutable."
                )

        errors.extend(self.validate_dependencies())

        if self.has_dependency_cycle():
            errors.append("ExecutionPlan contiene un ciclo de dependencias.")

        return errors

    def is_valid(self) -> bool:
        return not self.validate()

    # =========================================================
    # Status
    # =========================================================

    def mark_planned(self) -> None:
        self.status = "planned"

    def mark_validated(self) -> None:
        self.status = "validated"

    def mark_running(self) -> None:
        self.status = "running"

    def mark_completed(self) -> None:
        self.status = "completed"

    def mark_partial(self) -> None:
        self.status = "partial"

    def mark_failed(self) -> None:
        self.status = "failed"

    def mark_cancelled(self) -> None:
        self.status = "cancelled"

    # =========================================================
    # Serialization
    # =========================================================

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
            "steps": [step.to_dict(include_result=include_step_results) for step in self.steps],
        }

        if include_runtime:
            data["loaded_context"] = dict(self.loaded_context)
            data["execution_context"] = dict(self.execution_context)

        return data

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> ExecutionPlan:
        if not isinstance(data, dict):
            raise ValueError("ExecutionPlan.from_dict requiere un diccionario.")

        created_at_value = data.get("created_at")

        if created_at_value:
            try:
                created_at = datetime.fromisoformat(created_at_value)
            except (TypeError, ValueError) as exc:
                raise ValueError("ExecutionPlan.created_at inválido.") from exc
        else:
            created_at = datetime.now(timezone.utc)

        raw_steps = data.get(
            "steps",
            [],
        )

        if not isinstance(raw_steps, list):
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

        if not isinstance(raw_params, dict):
            raise ValueError("ExecutionPlan.params debe ser un diccionario.")

        if not isinstance(raw_constraints, list):
            raise ValueError("ExecutionPlan.constraints debe ser una lista.")

        if not isinstance(raw_context, dict):
            raise ValueError("ExecutionPlan.context_requirements debe " "ser un diccionario.")

        if not isinstance(raw_governance, dict):
            raise ValueError("ExecutionPlan.governance debe ser un diccionario.")

        if not isinstance(raw_policy, dict):
            raise ValueError("ExecutionPlan.execution_policy debe " "ser un diccionario.")

        if not isinstance(raw_loaded_context, dict):
            raise ValueError("ExecutionPlan.loaded_context debe " "ser un diccionario.")

        if not isinstance(raw_execution_context, dict):
            raise ValueError("ExecutionPlan.execution_context debe " "ser un diccionario.")

        if not isinstance(raw_metadata, dict):
            raise ValueError("ExecutionPlan.metadata debe ser un diccionario.")

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
            metadata=dict(raw_metadata),
        )

    # =========================================================
    # Representation
    # =========================================================

    def __repr__(self) -> str:
        return (
            "<ExecutionPlan("
            f"id={self.id}, "
            f"status={self.status}, "
            f"intent={self.intent}, "
            f"mode={self.execution_mode}, "
            f"unit={self.execution_unit_type}:"
            f"{self.execution_unit}, "
            f"steps={len(self.steps)}"
            ")>"
        )

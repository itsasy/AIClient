from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from core.execution_step import ExecutionStep
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout


@dataclass(slots=True)
class ExecutionPlan:
    """
    Contrato central de ejecución de AIClient.

    ExecutionPlan es la fuente de verdad de una ejecución.

    El plan es construido por Planning y consumido por Runtime.

    Responsabilidades:

        - representar la intención que originó la ejecución;
        - definir el objetivo;
        - definir la modalidad de ejecución;
        - definir la unidad ejecutable o los steps;
        - definir dependencias;
        - declarar requisitos de contexto;
        - declarar governance/policy;
        - conservar metadata de planificación;
        - controlar el lifecycle del plan;
        - serializar/deserializar el contrato.

    No:

        - ejecuta Agents;
        - ejecuta Skills;
        - descubre unidades;
        - interpreta lenguaje natural;
        - resuelve proveedores LLM;
        - carga contexto por sí mismo.
    """

    # =========================================================
    # Constants
    # =========================================================

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
            "paused",
            "not_available",
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
        "memory": False,
        "obsidian": False,
        "gentleman": False,
        "standards": False,
        "documents": False,
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
    # Runtime
    # =========================================================

    loaded_context: dict[str, Any] = field(default_factory=dict)

    execution_context: dict[str, Any] = field(default_factory=dict)

    result: Any = None

    error: str | None = None

    # =========================================================
    # Metadata
    # =========================================================

    metadata: dict[str, Any] = field(default_factory=dict)

    # =========================================================
    # Initialization
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
    def _normalize_text(
        value: str,
    ) -> str:
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
                f"Tipos permitidos: "
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
                f"Modos permitidos: "
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
                f"Estados permitidos: "
                f"{sorted(cls.VALID_STATUSES)}"
            )

        return value

    # =========================================================
    # Container validation
    # =========================================================

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
        normalized: dict[str, bool] = {}

        for provider, required in self.context_requirements.items():
            if not isinstance(provider, str):
                raise ValueError("Los nombres de providers de contexto " "deben ser strings.")

            normalized_provider = provider.lower().strip()

            if not normalized_provider:
                raise ValueError("El nombre del provider de contexto " "no puede estar vacío.")

            if not isinstance(required, bool):
                raise ValueError(f"context_requirements.{provider} " "debe ser booleano.")

            normalized[normalized_provider] = required

        self.context_requirements = normalized

    def requires_context(
        self,
        provider: str,
    ) -> bool:
        if not isinstance(provider, str):
            return False

        provider = provider.lower().strip()

        if not provider:
            return False

        return bool(
            self.context_requirements.get(
                provider,
                False,
            )
        )

    def set_context_requirement(
        self,
        provider: str,
        required: bool,
    ) -> None:
        if not isinstance(provider, str):
            raise ValueError("El provider de contexto debe ser un string.")

        provider = provider.lower().strip()

        if not provider:
            raise ValueError("El provider de contexto no puede estar vacío.")

        if not isinstance(required, bool):
            raise ValueError("required debe ser booleano.")

        self.context_requirements[provider] = required

    def required_context_providers(self) -> list[str]:
        """API oficial para ContextManager."""
        requirements = getattr(self, "context_requirements", None) or {}
        if not isinstance(requirements, dict):
            return []
        return [key for key, required in requirements.items() if required]

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
                f"Modos permitidos: "
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
            raise ValueError("execution_policy.autonomous " "debe ser booleano.")

        self.execution_policy["autonomous"] = autonomous

        max_retries = self.execution_policy.get(
            "max_retries",
            2,
        )

        if isinstance(max_retries, bool) or not isinstance(max_retries, int) or max_retries < 0:
            raise ValueError(
                "execution_policy.max_retries debe ser " "un entero mayor o igual a cero."
            )

        self.execution_policy["max_retries"] = max_retries

        requires_approval = self.execution_policy.get(
            "requires_approval",
            False,
        )

        if not isinstance(requires_approval, bool):
            raise ValueError("execution_policy.requires_approval " "debe ser booleano.")

        self.execution_policy["requires_approval"] = requires_approval

        stop_on_error = self.execution_policy.get(
            "stop_on_error",
            True,
        )

        if not isinstance(stop_on_error, bool):
            raise ValueError("execution_policy.stop_on_error " "debe ser booleano.")

        self.execution_policy["stop_on_error"] = stop_on_error

        timeout = self.execution_policy.get(
            "timeout",
            300,
        )

        if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout <= 0:
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

    # =========================================================
    # Steps
    # =========================================================

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

    # =========================================================
    # Validation
    # =========================================================

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

    # =========================================================
    # Lifecycle
    # =========================================================

    @property
    def is_terminal(self) -> bool:
        return self.status in {
            "completed",
            "partial",
            "failed",
            "cancelled",
        }

    @property
    def is_success(self) -> bool:
        return self.status == "completed"

    @property
    def is_failed(self) -> bool:
        return self.status == "failed"

    @property
    def is_partial(self) -> bool:
        return self.status == "partial"

    @property
    def is_running(self) -> bool:
        return self.status == "running"

    @property
    def is_pending(self) -> bool:
        return self.status == "pending"

    @property
    def is_planned(self) -> bool:
        return self.status == "planned"

    @property
    def is_validated(self) -> bool:
        return self.status == "validated"

    def _set_status(
        self,
        status: str,
    ) -> None:
        self.status = self.normalize_status(status)

    def mark_planned(self) -> None:
        self._set_status("planned")

    def mark_validated(self) -> None:
        errors = self.validate()

        if errors:
            raise ValueError("No se puede validar ExecutionPlan: " + "; ".join(errors))

        self._set_status("validated")

    def mark_running(self) -> None:
        if self.status not in {
            "planned",
            "validated",
            "running",
        }:
            raise ValueError("ExecutionPlan debe estar planned o " "validated antes de ejecutarse.")

        self._set_status("running")

    def mark_completed(
        self,
        result: Any = None,
    ) -> None:
        self.result = result
        self.error = None
        self._set_status("completed")

    def mark_partial(
        self,
        result: Any = None,
        error: str | None = None,
    ) -> None:
        self.result = result
        self.error = str(error) if error is not None else None
        self._set_status("partial")

    def mark_failed(self, error: str | None = None) -> None:
        """
        Marca el plan como fallido.

        error puede ser None; se normaliza a un mensaje no vacío
        para no romper callers y mantener self.error siempre definido.
        """
        msg = (error or "").strip() or "Plan failed"
        self.result = None
        self.error = msg
        self.metadata["last_error"] = msg
        self._set_status("failed")

    def mark_cancelled(
        self,
        reason: str | None = None,
    ) -> None:
        if reason:
            self.metadata["cancel_reason"] = str(reason)

        self._set_status("cancelled")

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

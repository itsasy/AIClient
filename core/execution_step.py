from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, ClassVar


@dataclass(slots=True)
class ExecutionStep:
    """
    Unidad atómica de trabajo dentro de un ExecutionPlan.

    Responsabilidades:
        - Describir qué unidad ejecutar (agent/skill)
        - Declarar dependencias
        - Mantener su propio estado de lifecycle
        - Exponer max_retries / retry_count

    No decide retries ni evalúa resultados.
    """

    VALID_UNIT_TYPES: ClassVar[frozenset[str]] = frozenset({"agent", "skill"})

    VALID_STATUSES: ClassVar[frozenset[str]] = frozenset(
        {"pending", "running", "completed", "failed", "skipped"}
    )

    # Transiciones permitidas
    VALID_TRANSITIONS: ClassVar[dict[str, frozenset[str]]] = {
        "pending": frozenset({"running", "skipped"}),
        "running": frozenset({"completed", "failed", "skipped"}),
        "failed": frozenset({"pending"}),  # reset / retry
        "completed": frozenset({"pending"}),  # reset
        "skipped": frozenset({"pending"}),  # reset
    }

    description: str
    unit_type: str
    unit_name: str

    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    params: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)

    expected_output: str | None = None

    # Configuración de retries (no contador)
    max_retries: int = 0

    # Contador de retries consumidos
    retry_count: int = 0

    timeout: int = 120

    status: str = "pending"
    result: Any = None
    error: str | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.description = self._normalize_required(self.description, "description")
        self.unit_type = self._normalize_unit_type(self.unit_type)
        self.unit_name = self._normalize_required(self.unit_name, "unit_name")
        self.expected_output = self._normalize_optional(self.expected_output)

        if not isinstance(self.params, dict):
            raise ValueError("ExecutionStep.params debe ser un diccionario.")
        if not isinstance(self.metadata, dict):
            raise ValueError("ExecutionStep.metadata debe ser un diccionario.")

        self.depends_on = self._normalize_dependencies(self.depends_on)
        self.max_retries = self._validate_non_negative_int(self.max_retries, "max_retries")
        self.retry_count = self._validate_non_negative_int(self.retry_count, "retry_count")
        self.timeout = self._validate_positive_int(self.timeout, "timeout")
        self.status = self._normalize_status(self.status)

        if not self.id or not str(self.id).strip():
            self.id = str(uuid.uuid4())
        else:
            self.id = str(self.id).strip()

    # =========================================================
    # Normalization helpers
    # =========================================================

    @staticmethod
    def _normalize_required(value: str, field_name: str) -> str:
        if not isinstance(value, str):
            raise ValueError(f"ExecutionStep.{field_name} debe ser un string.")
        value = value.strip()
        if not value:
            raise ValueError(f"ExecutionStep.{field_name} no puede estar vacío.")
        return value

    @staticmethod
    def _normalize_optional(value: str | None) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("ExecutionStep.expected_output debe ser string o None.")
        value = value.strip()
        return value or None

    @classmethod
    def _normalize_unit_type(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("ExecutionStep.unit_type debe ser un string.")
        normalized = value.lower().strip().replace("-", "_").replace(" ", "_")
        if normalized not in cls.VALID_UNIT_TYPES:
            raise ValueError(
                f"Tipo de unidad inválido: {normalized}. "
                f"Tipos permitidos: {sorted(cls.VALID_UNIT_TYPES)}"
            )
        return normalized

    @classmethod
    def _normalize_status(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("ExecutionStep.status debe ser un string.")
        normalized = value.lower().strip()
        if normalized not in cls.VALID_STATUSES:
            raise ValueError(
                f"Estado de step inválido: {normalized}. "
                f"Estados permitidos: {sorted(cls.VALID_STATUSES)}"
            )
        return normalized

    @staticmethod
    def _normalize_dependencies(dependencies: list[str]) -> list[str]:
        if not isinstance(dependencies, list):
            raise ValueError("ExecutionStep.depends_on debe ser una lista.")
        normalized: list[str] = []
        for dep in dependencies:
            if not isinstance(dep, str):
                raise ValueError("Cada dependencia debe ser un string.")
            dep = dep.strip()
            if dep and dep not in normalized:
                normalized.append(dep)
        return normalized

    @staticmethod
    def _validate_non_negative_int(value: int, field_name: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"ExecutionStep.{field_name} debe ser un entero.")
        if value < 0:
            raise ValueError(f"ExecutionStep.{field_name} no puede ser negativo.")
        return value

    @staticmethod
    def _validate_positive_int(value: int, field_name: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"ExecutionStep.{field_name} debe ser un entero.")
        if value <= 0:
            raise ValueError(f"ExecutionStep.{field_name} debe ser mayor que cero.")
        return value

    # =========================================================
    # State properties
    # =========================================================

    @property
    def is_terminal(self) -> bool:
        return self.status in {"completed", "failed", "skipped"}

    @property
    def is_success(self) -> bool:
        return self.status == "completed"

    @property
    def is_failed(self) -> bool:
        return self.status == "failed"

    @property
    def is_skipped(self) -> bool:
        return self.status == "skipped"

    @property
    def is_pending(self) -> bool:
        return self.status == "pending"

    @property
    def is_running(self) -> bool:
        return self.status == "running"

    @property
    def can_retry(self) -> bool:
        return self.retry_count < self.max_retries

    # =========================================================
    # Lifecycle (con validación de transiciones)
    # =========================================================

    def _transition(self, new_status: str) -> None:
        allowed = self.VALID_TRANSITIONS.get(self.status, frozenset())
        if new_status not in allowed:
            raise ValueError(
                f"Transición inválida de '{self.status}' → '{new_status}'. "
                f"Permitidas: {sorted(allowed)}"
            )
        self.status = new_status

    def mark_running(self) -> None:
        self._transition("running")
        self.result = None
        self.error = None

    def mark_completed(self, result: Any = None) -> None:
        self._transition("completed")
        self.result = result
        self.error = None

    def mark_failed(self, error: str) -> None:
        self._transition("failed")
        self.result = None
        self.error = str(error)

    def mark_skipped(self, reason: str | None = None) -> None:
        self._transition("skipped")
        self.result = None
        self.error = None
        if reason:
            self.metadata["skip_reason"] = reason

    def apply_result(
        self,
        result: Any,
        success: bool,
        error: str | None = None,
    ) -> None:
        if success:
            self.mark_completed(result)
        else:
            self.mark_failed(error or "La ejecución del step falló.")

    def reset(self) -> None:
        """Vuelve a pending (usado en retries)."""
        if self.status not in {"failed", "completed", "skipped"}:
            # Si está pending o running, no forzamos
            if self.status == "pending":
                return
            raise ValueError(f"No se puede resetear un step en estado '{self.status}'.")
        self._transition("pending")
        self.result = None
        self.error = None

    def increment_retry(self) -> None:
        self.retry_count += 1

    # =========================================================
    # Dependencies
    # =========================================================

    def add_dependency(self, step_id: str) -> None:
        if not step_id or not str(step_id).strip():
            raise ValueError("El ID de dependencia no puede estar vacío.")
        step_id = str(step_id).strip()
        if step_id == self.id:
            raise ValueError("ExecutionStep no puede depender de sí mismo.")
        if step_id not in self.depends_on:
            self.depends_on.append(step_id)

    def remove_dependency(self, step_id: str) -> bool:
        if step_id in self.depends_on:
            self.depends_on.remove(step_id)
            return True
        return False

    def has_dependencies(self) -> bool:
        return bool(self.depends_on)

    # =========================================================
    # Serialization
    # =========================================================

    def to_dict(self, include_result: bool = True) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "description": self.description,
            "unit_type": self.unit_type,
            "unit_name": self.unit_name,
            "params": dict(self.params),
            "depends_on": list(self.depends_on),
            "expected_output": self.expected_output,
            "max_retries": self.max_retries,
            "retry_count": self.retry_count,
            "timeout": self.timeout,
            "status": self.status,
            "error": self.error,
            "metadata": dict(self.metadata),
        }
        if include_result:
            data["result"] = self.result
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutionStep:
        if not isinstance(data, dict):
            raise ValueError("ExecutionStep.from_dict requiere un diccionario.")

        # Compatibilidad hacia atrás: si viene "retries", lo tratamos como max_retries
        max_retries = data.get("max_retries")
        if max_retries is None:
            max_retries = data.get("retries", 0)

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            description=data.get("description", ""),
            unit_type=data.get("unit_type", ""),
            unit_name=data.get("unit_name", ""),
            params=data.get("params", {}),
            depends_on=data.get("depends_on", []),
            expected_output=data.get("expected_output"),
            max_retries=max_retries,
            retry_count=data.get("retry_count", 0),
            timeout=data.get("timeout", 120),
            status=data.get("status", "pending"),
            result=data.get("result"),
            error=data.get("error"),
            metadata=data.get("metadata", {}),
        )

    def __repr__(self) -> str:
        return (
            f"<ExecutionStep("
            f"id={self.id}, "
            f"unit={self.unit_type}:{self.unit_name}, "
            f"status={self.status}, "
            f"retry={self.retry_count}/{self.max_retries})>"
        )

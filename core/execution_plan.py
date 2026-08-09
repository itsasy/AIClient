from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from core.execution_step import ExecutionStep

UNIT_ALIASES = {
    "agents": "agent",
    "agent_runtime": "agent",
    "skills": "skill",
    "skill_runtime": "skill",
}
UNIT_TYPES = {"agent", "skill"}


@dataclass(slots=True)
class ExecutionPlan:
    """
    Contrato central de ejecución de AIClient.

    Este objeto es la fuente de verdad para toda ejecución.
    Contiene todo lo necesario para que el sistema ejecute
    una tarea sin reinterpretar la intención.
    """

    VALID_EXECUTION_MODES = frozenset({"single", "multi_step"})
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

    # ==========================================================
    # Identidad y metadatos
    # ==========================================================

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "pending"

    # ==========================================================
    # Intención del usuario (interpretada una sola vez)
    # ==========================================================

    original_task: str = ""
    intent: str | None = None
    intent_category: str | None = None
    objective: str | None = None

    # ==========================================================
    # Ejecución
    # ==========================================================

    execution_mode: str = "single"  # "single" | "multi_step"
    execution_unit_type: str | None = None  # "agent" | "skill"
    execution_unit: str | None = None  # nombre del agente o skill

    # ==========================================================
    # Parámetros y restricciones
    # ==========================================================

    params: dict[str, Any] = field(default_factory=dict)
    constraints: list[str] = field(default_factory=list)

    # ==========================================================
    # REQUISITOS DE CONTEXTO (nuevo)
    # ==========================================================
    #
    # Define qué contexto debe cargar ContextManager.
    # Cada clave es un proveedor de contexto.
    # El valor indica si debe cargarse.
    #
    # Valores posibles:
    #   - project: inspección del proyecto
    #   - engram: memoria persistente
    #   - obsidian: segundo cerebro
    #   - gentleman: skills externas
    #   - standards: estándares aprendidos
    #   - documents: documentos ingeridos
    #   - memory: historial conversacional
    #
    # Por defecto, nada se carga.
    # Esto garantiza que "hola" no cargue contexto innecesario.
    # ==========================================================

    context_requirements: dict[str, bool] = field(
        default_factory=lambda: {
            "project": False,
            "engram": False,
            "obsidian": False,
            "gentleman": False,
            "standards": False,
            "documents": False,
            "memory": False,
        }
    )

    # ==========================================================
    # GOBERNANZA (nuevo)
    # ==========================================================
    #
    # Define las restricciones de seguridad y permisos.
    # Afecta a Skills que interactúan con el sistema operativo.
    # ==========================================================

    governance: dict[str, Any] = field(
        default_factory=lambda: {
            "mode": "safe",  # "safe" | "powerful"
            "allow_shell": False,
            "allow_network": False,
            "allow_write": False,
            "allow_sudo": False,
        }
    )

    # ==========================================================
    # POLÍTICA DE EJECUCIÓN (nuevo)
    # ==========================================================
    #
    # Define cómo se comporta ExecutionEngine.
    # ==========================================================

    execution_policy: dict[str, Any] = field(
        default_factory=lambda: {
            "autonomous": False,  # si es True, no pide confirmación
            "max_retries": 2,
            "requires_approval": False,
            "stop_on_error": True,
            "timeout": 300,
        }
    )

    # ==========================================================
    # Pasos (para modo multi_step)
    # ==========================================================

    steps: list[ExecutionStep] = field(default_factory=list)

    # ==========================================================
    # Contexto cargado (runtime)
    # ==========================================================

    loaded_context: dict[str, Any] = field(default_factory=dict)
    execution_context: dict[str, Any] = field(default_factory=dict)

    # ==========================================================
    # Metadatos (solo para información adicional)
    # ==========================================================

    metadata: dict[str, Any] = field(default_factory=dict)

    # ==========================================================
    # Métodos de clase para normalización
    # ==========================================================

    @classmethod
    def normalize_unit_type(cls, unit_type: str | None) -> str | None:
        if not unit_type:
            return None
        value = unit_type.lower().strip().replace("-", "_").replace(" ", "_")
        return UNIT_ALIASES.get(value, value)

    @classmethod
    def normalize_execution_mode(cls, mode: str | None) -> str:
        if not mode:
            return "single"
        value = mode.lower().strip().replace("-", "_").replace(" ", "_")
        if value not in cls.VALID_EXECUTION_MODES:
            return "single"
        return value

    # ==========================================================
    # Lifecycle
    # ==========================================================

    def __post_init__(self) -> None:
        self.original_task = self.original_task.strip()
        self.execution_mode = self.normalize_execution_mode(self.execution_mode)

        if self.execution_mode not in self.VALID_EXECUTION_MODES:
            raise ValueError(
                f"Modo de ejecución inválido: {self.execution_mode}. "
                f"Modos permitidos: {sorted(self.VALID_EXECUTION_MODES)}"
            )

        if self.execution_unit_type is not None:
            self.execution_unit_type = self.normalize_unit_type(self.execution_unit_type)

        if self.execution_unit is not None:
            self.execution_unit = self.execution_unit.strip()

        if self.execution_unit_type is not None:
            if self.execution_unit_type not in ExecutionStep.VALID_UNIT_TYPES:
                raise ValueError(
                    f"Tipo de unidad inválido: {self.execution_unit_type}. "
                    f"Tipos permitidos: {sorted(ExecutionStep.VALID_UNIT_TYPES)}"
                )
            if not self.execution_unit:
                raise ValueError(
                    "execution_unit es obligatorio cuando execution_unit_type está definido."
                )

        if self.status not in self.VALID_STATUSES:
            raise ValueError(
                f"Estado de plan inválido: {self.status}. "
                f"Estados permitidos: {sorted(self.VALID_STATUSES)}"
            )

        # Normalizar governance
        if "mode" in self.governance:
            self.governance["mode"] = self.governance["mode"].lower().strip()

    # ==========================================================
    # Context helpers
    # ==========================================================

    def requires_context(self, provider: str) -> bool:
        """Devuelve True si el plan requiere un proveedor de contexto específico."""
        return self.context_requirements.get(provider, False)

    def set_context_requirement(self, provider: str, required: bool) -> None:
        """Establece un requisito de contexto."""
        self.context_requirements[provider] = required

    # ==========================================================
    # Governance helpers
    # ==========================================================

    def is_safe_mode(self) -> bool:
        return self.governance.get("mode", "safe") == "safe"

    def is_powerful_mode(self) -> bool:
        return self.governance.get("mode", "safe") == "powerful"

    def allows_shell(self) -> bool:
        return self.governance.get("allow_shell", False)

    def allows_network(self) -> bool:
        return self.governance.get("allow_network", False)

    def allows_write(self) -> bool:
        return self.governance.get("allow_write", False)

    def allows_sudo(self) -> bool:
        return self.governance.get("allow_sudo", False)

    # ==========================================================
    # Policy helpers
    # ==========================================================

    def is_autonomous(self) -> bool:
        return self.execution_policy.get("autonomous", False)

    def get_max_retries(self) -> int:
        return self.execution_policy.get("max_retries", 2)

    def requires_approval(self) -> bool:
        return self.execution_policy.get("requires_approval", False)

    def get_timeout(self) -> int:
        return self.execution_policy.get("timeout", 300)

    # ==========================================================
    # Steps
    # ==========================================================

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
        step = ExecutionStep(
            description=description,
            unit_type=self.normalize_unit_type(unit_type) or unit_type,
            unit_name=unit_name,
            params=params or {},
            expected_output=expected_output,
            retries=retries,
            timeout=timeout,
            metadata=metadata or {},
        )
        self.steps.append(step)
        return step

    def has_steps(self) -> bool:
        return bool(self.steps)

    def is_multi_step(self) -> bool:
        return self.execution_mode == "multi_step"

    # ==========================================================
    # Validation
    # ==========================================================

    def validate(self) -> list[str]:
        errors = []

        if not self.original_task:
            errors.append("ExecutionPlan requiere original_task.")

        if not self.intent:
            errors.append("ExecutionPlan requiere intent.")

        if self.execution_mode == "single":
            if not self.execution_unit_type or not self.execution_unit:
                errors.append("Modo single requiere execution_unit_type y execution_unit.")
            if self.steps:
                errors.append("Modo single no permite steps.")
        elif self.execution_mode == "multi_step":
            if not self.steps and not self.execution_unit:
                errors.append("Modo multi_step requiere al menos un step o una unidad ejecutable.")

        step_ids = {step.id for step in self.steps}
        for step in self.steps:
            for dep in step.depends_on:
                if dep not in step_ids:
                    errors.append(f"Step {step.id} depende de {dep}, que no existe.")

        return errors

    def is_valid(self) -> bool:
        return not bool(self.validate())

    # ==========================================================
    # Status
    # ==========================================================

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

    # ==========================================================
    # Serialization
    # ==========================================================

    def to_dict(self) -> dict[str, Any]:
        return {
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
            "max_retries": self.get_max_retries(),
            "stop_on_error": self.execution_policy.get("stop_on_error", True),
            "loaded_context": dict(self.loaded_context),
            "execution_context": dict(self.execution_context),
            "metadata": dict(self.metadata),
            "steps": [step.to_dict() for step in self.steps],
        }

    def __repr__(self) -> str:
        return (
            f"<ExecutionPlan("
            f"id={self.id}, "
            f"status={self.status}, "
            f"intent={self.intent}, "
            f"unit={self.execution_unit_type}:{self.execution_unit}, "
            f"steps={len(self.steps)})>"
        )

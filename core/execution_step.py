from __future__ import annotations

import uuid

from dataclasses import dataclass, field

from typing import Any

VALID_STEP_STATUS = {
    "pending",
    "running",
    "completed",
    "failed",
    "skipped",
}


@dataclass(slots=True)
class ExecutionStep:
    """
    Unidad individual de ejecución.

    Representa:

    - Qué ejecutar.
    - Cómo ejecutarlo.
    - Dependencias.
    - Estado.

    No:

    - Ejecuta lógica.
    - Decide estrategia.
    - Gestiona runtime.
    """

    id: str = field(
        default_factory=lambda: str(uuid.uuid4()),
    )

    description: str = ""

    unit_type: str = ""

    unit_name: str = ""

    params: dict[str, Any] = field(
        default_factory=dict,
    )

    depends_on: list[str] = field(
        default_factory=list,
    )

    status: str = "pending"

    result: Any = None

    error: str | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict,
    )

    # ==================================================
    # Lifecycle
    # ==================================================

    def set_status(
        self,
        status: str,
    ) -> None:

        status = self.normalize(
            status,
        )

        if status not in VALID_STEP_STATUS:

            raise ValueError(f"Estado de step inválido: {status}")

        self.status = status

    def mark_running(
        self,
    ) -> None:

        self.set_status(
            "running",
        )

    def mark_completed(
        self,
        result: Any = None,
    ) -> None:

        self.set_status(
            "completed",
        )

        self.result = result
        self.error = None

    def mark_failed(
        self,
        error: str,
    ) -> None:

        self.set_status(
            "failed",
        )

        self.error = error

    # ==================================================
    # Validation
    # ==================================================

    def validate(
        self,
    ) -> list[str]:

        errors: list[str] = []

        if not self.description.strip():

            errors.append(
                "step sin descripción",
            )

        if not self.unit_type:

            errors.append(
                "step sin unit_type",
            )

        if not self.unit_name:

            errors.append(
                "step sin unit_name",
            )

        if self.status not in VALID_STEP_STATUS:

            errors.append(
                "step con estado inválido",
            )

        if self.status == "failed" and not self.error:

            errors.append(
                "step fallido requiere error",
            )

        return errors

    # ==================================================
    # Helpers
    # ==================================================

    @staticmethod
    def normalize(
        value: str,
    ) -> str:

        if not value:

            return ""

        return (
            value.lower()
            .strip()
            .replace(
                "-",
                "_",
            )
            .replace(
                " ",
                "_",
            )
        )

    # ==================================================
    # Serialization
    # ==================================================

    def to_dict(
        self,
    ) -> dict[str, Any]:

        return {
            "id": self.id,
            "description": self.description,
            "unit_type": self.unit_type,
            "unit_name": self.unit_name,
            "params": dict(self.params),
            "depends_on": list(self.depends_on),
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "metadata": dict(self.metadata),
        }

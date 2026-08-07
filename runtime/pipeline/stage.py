from __future__ import annotations

from dataclasses import dataclass, field

from typing import Any, Callable


@dataclass(slots=True)
class PipelineStage:
    """
    Etapa individual dentro del pipeline.

    Representa una transformación del flujo.

    No:

    - Ejecuta agentes.
    - Ejecuta skills.
    - Gestiona lifecycle del plan.
    """

    name: str

    handler: Callable[..., Any]

    enabled: bool = True

    metadata: dict[str, Any] = field(
        default_factory=dict,
    )

    def execute(
        self,
        payload: Any,
        **kwargs: Any,
    ) -> Any:

        if not self.enabled:

            return payload

        return self.handler(
            payload,
            **kwargs,
        )

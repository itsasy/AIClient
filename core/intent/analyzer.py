from __future__ import annotations

import logging

from core.intent.detectors import IntentDetectors
from core.intent.models import IntentResult

logger = logging.getLogger(__name__)


class IntentAnalyzer:
    """
    Fachada pública del sistema de intención.

    Responsabilidades:

    - Recibir consultas.
    - Delegar detección.
    - Garantizar resultado válido.

    No:

    - Contiene reglas.
    - Crea planes.
    - Selecciona agentes.
    - Selecciona skills.
    - Ejecuta acciones.
    """

    def __init__(
        self,
        detector: type[IntentDetectors] = IntentDetectors,
    ):
        self.detector = detector

    # ==================================================
    # Analysis
    # ==================================================

    def analyze(
        self,
        query: str,
    ) -> IntentResult:

        if not query or not query.strip():

            return IntentResult(
                intent="conversation",
                domain="conversation",
            )

        result = self.detector.detect(
            query,
        )

        if result:

            return result

        logger.debug(
            "Intent no detectado, fallback conversation query=%s",
            query[:100],
        )

        return IntentResult(
            intent="conversation",
            domain="conversation",
            entities={
                "task": query,
            },
        )

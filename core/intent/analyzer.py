from __future__ import annotations

import logging

from core.intent.detectors import IntentDetectors
from core.intent.models import IntentResult

logger = logging.getLogger(__name__)


class IntentAnalyzer:
    """
    Fachada pública del sistema de análisis de intención.

    Responsabilidades:

    - Recibir una consulta.
    - Ejecutar detección de intención.
    - Garantizar siempre un IntentResult válido.

    No:

    - Construye ExecutionPlans.
    - Ejecuta acciones.
    - Selecciona agentes.
    - Selecciona skills.
    - Gestiona contexto.
    """

    name = "intent_analyzer"

    def __init__(
        self,
        detector: type[IntentDetectors] = IntentDetectors,
    ) -> None:

        self.detector = detector

    # ======================================================
    # Public API
    # ======================================================

    def analyze(
        self,
        query: str,
    ) -> IntentResult:

        if not query or not query.strip():

            return IntentResult(
                intent="conversation",
                domain="conversation",
                confidence=0.0,
                signals=[
                    "empty_query",
                ],
            )

        result = self.detector.detect(
            query,
        )

        if result:

            logger.debug(
                "Intent detectado intent=%s confidence=%s",
                result.intent,
                result.confidence,
            )

            return result

        logger.debug(
            "Intent fallback conversation query=%s",
            query[:100],
        )

        return IntentResult(
            intent="conversation",
            domain="conversation",
            category="general",
            confidence=0.0,
            entities={
                "task": query,
            },
            signals=[
                "fallback",
            ],
        )

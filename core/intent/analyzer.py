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
    - Ejecutar detectores.
    - Garantizar siempre un IntentResult.

    No:

    - construye ExecutionPlans;
    - ejecuta acciones;
    - selecciona agentes;
    - selecciona skills;
    - gestiona contexto.
    """

    name = "intent_analyzer"

    def __init__(
        self,
        detector: type[IntentDetectors] = IntentDetectors,
    ) -> None:
        self.detector = detector

    def analyze(
        self,
        query: str,
    ) -> IntentResult:

        normalized_query = query.strip() if isinstance(query, str) else ""

        if not normalized_query:
            return IntentResult(
                intent="conversation",
                domain="conversation",
                category="general",
                complexity="low",
                confidence=0.0,
                entities={},
                signals=[
                    "empty_query",
                ],
                original_query="",
            )

        result = self.detector.detect(
            normalized_query,
        )

        if result is not None:
            logger.debug(
                "Intent detectado intent=%s domain=%s " "confidence=%.2f",
                result.intent,
                result.domain,
                result.confidence,
            )

            return result

        logger.debug(
            "Intent fallback conversation query=%s",
            normalized_query[:100],
        )

        return IntentResult(
            intent="conversation",
            domain="conversation",
            category="general",
            complexity="low",
            confidence=0.0,
            entities={
                "task": normalized_query,
            },
            signals=[
                "fallback",
            ],
            original_query=normalized_query,
        )

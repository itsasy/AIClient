from __future__ import annotations

import json
import logging
from typing import Any

from agents.base import Agent

from core.execution_plan import ExecutionPlan

from llm.prompt_builder import PromptBuilder
from llm.provider_manager import ProviderManager
from llm.provider_selector import ProviderSelector

logger = logging.getLogger(__name__)


class SelfCriticAgent(Agent):
    """
    Agente encargado de evaluar la calidad de una respuesta generada.
    """

    name = "self_critic"

    role = "Evaluador de calidad"

    def __init__(self):

        self.provider_manager = ProviderManager()

    def process(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:

        context = dict(context or {})

        provider, fallback = ProviderSelector.select(
            plan,
        )

        critique_plan = ExecutionPlan(
            original_task=plan.original_task,
            objective="Evaluar la respuesta generada",
            intent="reflection",
            execution_unit_type="agent",
            execution_unit="self_critic",
            execution_mode="single",
        )

        critique_plan.params = dict(plan.params)

        critique_plan.context_requirements = list(
            plan.context_requirements,
        )

        critique_plan.metadata = dict(
            plan.metadata,
        )

        prompt = PromptBuilder.build(
            plan=critique_plan,
            context={
                **context,
                "draft_response": context.get(
                    "draft_response",
                    "",
                ),
                "evaluation_mode": True,
            },
        )

        try:

            raw = self.provider_manager.generate(
                prompt=prompt,
                provider_name=provider,
                fallback_chain=fallback,
            )

            return self._extract_json(
                raw,
            )

        except Exception:

            logger.exception(
                "Error ejecutando SelfCritic.",
            )

            return self._fallback()

    # ==========================================================
    # Helpers
    # ==========================================================

    def _extract_json(
        self,
        text: str,
    ) -> dict[str, Any]:

        start = text.find("{")

        end = text.rfind("}") + 1

        if start == -1:

            raise ValueError(
                "JSON no encontrado.",
            )

        return json.loads(
            text[start:end],
        )

    def _fallback(
        self,
    ) -> dict[str, Any]:

        return {
            "alignment_score": 7,
            "hallucination_risk": "medium",
            "context_usage": "unknown",
            "coverage": "No evaluado",
            "missing_parts": "",
            "course_correction_advice": "",
            "summary": "Evaluación no disponible.",
        }

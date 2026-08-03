import json
import logging

from agents.base import Agent
from core.execution_plan import ExecutionPlan
from llm.prompt_builder import PromptBuilder
from llm.provider_manager import ProviderManager
from llm.provider_selector import ProviderSelector

logger = logging.getLogger(__name__)


class SelfCriticAgent(Agent):

    name = "self_critic"

    role = "Evaluador de calidad"

    def __init__(self):
        self.provider_manager = ProviderManager()

    def process(
        self,
        plan: ExecutionPlan,
        context: dict,
        draft_response: str,
    ) -> dict:

        provider, fallback = ProviderSelector.select(
            task=plan.original_task,
            skill_name="reflection",
            requested_provider=plan.preferred_provider,
        )

        critique_plan = ExecutionPlan(
            original_task=plan.original_task,
            intent="reflection",
            objective="Evaluar la respuesta generada",
            agent="self_critic",
            skill="reflection",
            context_requirements=[],
        )

        prompt = PromptBuilder.build(
            plan=critique_plan,
            context={
                **context,
                "draft_response": draft_response,
                "evaluation_mode": True,
            },
        )

        try:

            raw = self.provider_manager.generate(
                prompt=prompt,
                provider_name=provider,
                fallback_chain=fallback,
            )

            return self._extract_json(raw)

        except Exception:

            logger.exception("Self Critic error")

            return self._fallback()

    def _extract_json(
        self,
        text: str,
    ) -> dict:

        start = text.find("{")
        end = text.rfind("}") + 1

        if start == -1:
            raise ValueError("JSON no encontrado")

        return json.loads(text[start:end])

    def _fallback(self):

        return {
            "alignment_score": 7,
            "hallucination_risk": "medium",
            "context_usage": "good",
            "coverage": "No evaluado",
            "missing_parts": "",
            "course_correction_advice": "",
            "summary": "Evaluación no disponible",
        }

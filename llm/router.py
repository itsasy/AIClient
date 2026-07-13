import logging
import re

from llm.intent_analyzer import IntentAnalyzer
from llm.prompt_builder import PromptBuilder
from llm.provider_manager import ProviderManager
from llm.provider_selector import ProviderSelector
from skills.manager import SkillManager

logger = logging.getLogger(__name__)


class LLMRouter:
    skill_manager = SkillManager()
    provider_manager = ProviderManager()

    @staticmethod
    def detect_skill(query: str):
        if not query:
            return None, None
        result = IntentAnalyzer.analyze(query)
        return result.skill_name, result.skill_params

    @classmethod
    def generate(
        cls,
        task: str,
        context=None,
        skill_name=None,
        skill_params=None,
        provider_name: str | None = None,
        **kwargs,
    ) -> str:
        skill_result = cls._execute_skill(skill_name, skill_params)

        selected_provider = ProviderSelector.select(
            task=task,
            skill_name=skill_name,
            requested_provider=provider_name,
        )

        prompt = PromptBuilder.build(
            task=task,
            context=context or {},
            skill_name=skill_name,
            skill_result=skill_result,
        )

        logger.info(
            "Routing | skill=%s | provider=%s | len=%d",
            skill_name or "general",
            selected_provider,
            len(task),
        )

        return cls.provider_manager.generate(
            prompt=prompt,
            provider_name=selected_provider,
            **kwargs,
        )

    @classmethod
    def _execute_skill(cls, skill_name, skill_params=None):
        if not skill_name:
            return None
        logger.info("Skill: %s", skill_name)
        return cls.skill_manager.execute(skill_name, **(skill_params or {}))
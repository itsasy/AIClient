import logging

from core.config import Config
from core.execution_plan import ExecutionPlan

logger = logging.getLogger(__name__)


class ProviderSelector:
    """
    Selecciona proveedor LLM según ExecutionPlan.

    Prioridad:

        preferred_provider
                ↓
        intent_category
                ↓
        skills
                ↓
        agent
                ↓
        execution_mode
                ↓
        default
    """

    CATEGORY_MAP = {
        "code": (
            Config.CODE_PROVIDER,
            Config.CODE_FALLBACKS,
        ),
        "architecture": (
            Config.ARCHITECTURE_PROVIDER,
            Config.ARCHITECTURE_FALLBACKS,
        ),
        "documentation": (
            getattr(
                Config,
                "DOCUMENTATION_PROVIDER",
                Config.DEFAULT_PROVIDER,
            ),
            getattr(
                Config,
                "DOCUMENTATION_FALLBACKS",
                Config.DEFAULT_FALLBACKS,
            ),
        ),
        "fast": (
            getattr(
                Config,
                "FAST_PROVIDER",
                Config.DEFAULT_PROVIDER,
            ),
            getattr(
                Config,
                "FAST_FALLBACKS",
                Config.DEFAULT_FALLBACKS,
            ),
        ),
    }

    CATEGORY_ALIASES = {
        "project": "architecture",
        "planning": "architecture",
        "analysis": "architecture",
        "execution": "code",
        "file": "code",
        "conversation": "fast",
    }

    SKILL_CATEGORY = {
        "code": "code",
        "write_file": "code",
        "execute_code": "code",
        "shell": "code",
        "docker": "code",
        "sandbox": "code",
        "refactor_code": "code",
        "analyze_code": "code",
        "plan": "architecture",
        "architecture": "architecture",
        "analyze_project": "architecture",
        "reflection": "architecture",
        "self_critic": "architecture",
        "critique": "architecture",
        "readme": "documentation",
        "generate_proposal": "documentation",
        "conversation": "fast",
        "chat": "fast",
        "general": "fast",
        "quick": "fast",
        "learning": "fast",
    }

    AGENT_CATEGORY = {
        "coder": "code",
        "executor": "code",
        "architect": "architecture",
        "planner": "architecture",
        "task": "fast",
    }

    @classmethod
    def select(
        cls,
        plan: ExecutionPlan,
    ) -> tuple[str, list[str]]:

        if plan.preferred_provider:

            provider = plan.preferred_provider.lower()

            logger.info(
                "Provider forzado: %s",
                provider,
            )

            return (
                provider,
                cls._clean_chain(
                    provider,
                    Config.DEFAULT_FALLBACKS,
                ),
            )

        category = None

        if plan.intent_category:

            category = cls.CATEGORY_ALIASES.get(
                plan.intent_category.lower(),
                plan.intent_category.lower(),
            )

        if category is None and plan.skills:

            for skill in plan.skills:

                category = cls.SKILL_CATEGORY.get(
                    skill.lower(),
                )

                if category:
                    break

        if category is None and plan.agent:

            category = cls.AGENT_CATEGORY.get(
                plan.agent.lower(),
            )

        if category is None and plan.execution_mode == "multi_step":

            category = "architecture"

        if category is None:

            category = "fast"

        provider, fallbacks = cls.CATEGORY_MAP.get(
            category,
            (
                Config.DEFAULT_PROVIDER,
                Config.DEFAULT_FALLBACKS,
            ),
        )

        logger.info(
            "Provider=%s | Category=%s | Skills=%s | Agent=%s",
            provider,
            category,
            plan.skills,
            plan.agent,
        )

        return (
            provider,
            cls._clean_chain(
                provider,
                fallbacks,
            ),
        )

    @staticmethod
    def _clean_chain(
        provider: str,
        chain: list[str],
    ) -> list[str]:

        clean = []

        for item in chain:

            item = item.lower()

            if item == provider:
                continue

            if item not in clean:
                clean.append(item)

        return clean

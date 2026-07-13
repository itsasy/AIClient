import logging

from agents.manager import AgentManager
from core.context_builder import ContextBuilder
from core.memory import ConversationMemory
from llm.intent_analyzer import IntentAnalyzer

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self):
        self.context_builder = ContextBuilder()
        self.memory = ConversationMemory()
        self.agent_manager = AgentManager()

    def process(self, task: str) -> str:
        intent = IntentAnalyzer.analyze(task)

        logger.info(
            "Intención detectada | skill=%s | params=%s",
            intent.skill_name or "general",
            intent.skill_params or {},
        )

        context = self.context_builder.build(task)

        memory = self.memory.get_context()

        if memory:
            context["memory"] = memory

        response = self.agent_manager.delegate(
            task=task,
            context=context,
            skill_name=intent.skill_name,
            skill_params=intent.skill_params,
        )

        self.memory.add(task, response)

        return response
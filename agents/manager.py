import logging
import re

from agents.architect import ArchitectAgent
from agents.base import Agent
from agents.coder import CoderAgent
from agents.task_agent import TaskAgent


logger = logging.getLogger(__name__)


class AgentManager:
    def __init__(self):
        self.agents: dict[str, Agent] = {
            "architect": ArchitectAgent(),
            "coder": CoderAgent(),
            "task": TaskAgent(),
        }

    def select_agent(self, task: str) -> Agent:
        q = (task or "").lower().strip()

        architecture_intent = re.search(
            r"\b("
            r"arquitectura|arquitectónico|arquitectonico|"
            r"diseño|diseno|estándares|estandares|"
            r"estructura del proyecto|deuda técnica|deuda tecnica"
            r")\b",
            q,
        )

        if architecture_intent:
            return self.agents["architect"]

        code_intent = re.search(
            r"\b("
            r"código|codigo|función|funcion|clase|"
            r"script|endpoint|implementa|implementar|"
            r"refactor|refactoriza|bug"
            r")\b",
            q,
        )

        if code_intent:
            return self.agents["coder"]

        return self.agents["task"]

    def delegate(
        self,
        task: str,
        context: dict | None = None,
        skill_name: str | None = None,
        skill_params: dict | None = None,
    ) -> str:
        agent = self.select_agent(task)

        logger.info(
            "Delegando tarea al agente: %s",
            agent.name,
        )

        logger.info(
            "Contexto de ejecución | agent=%s | skill=%s",
            agent.name,
            skill_name or "general",
        )

        return agent.process(
            task=task,
            context=context or {},
            skill_name=skill_name,
            skill_params=skill_params,
        )
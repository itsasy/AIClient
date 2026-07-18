import logging
import re

from agents.architect import ArchitectAgent
from agents.base import Agent
from agents.coder import CoderAgent
from agents.task_agent import TaskAgent
from agents.multi_turn import MultiTurnAgent
from agents.executor import ExecutorAgent

logger = logging.getLogger(__name__)


class AgentManager:
    def __init__(self):
        self.agents: dict[str, Agent] = {
            "architect": ArchitectAgent(),
            "coder": CoderAgent(),
            "task": TaskAgent(),
            "multi_turn": MultiTurnAgent(),
            "executor": ExecutorAgent(),
        }

    def select_agent(self, task: str, skill_name: str | None = None) -> Agent:
        # 1. Si tenemos una skill_name detectada, la usamos para elegir agente
        if skill_name:
            # Skills de análisis/documentación → Arquitecto
            if skill_name in (
                "analyze",
                "analyze_project",
                "readme",
                "migrate_project",
                "refactor_code",
            ):
                return self.agents["architect"]

            # Skills de generación de código → Coder
            if skill_name in ("code", "generate_proposal"):
                return self.agents["coder"]

            # Skills de ejecución → Executor
            if skill_name in (
                "shell",
                "docker",
                "execute_code",
                "sandbox",
                "laravel_project",
                "full_project",
            ):
                return self.agents["executor"]

        # 2. Fallback: Lógica antigua por Regex
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
        agent = self.select_agent(task, skill_name)

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

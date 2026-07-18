import logging

from agents.architect import ArchitectAgent
from agents.base import Agent
from agents.coder import CoderAgent
from agents.executor import ExecutorAgent
from agents.multi_turn import MultiTurnAgent
from agents.task_agent import TaskAgent

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

        # Mapeo centralizado: skill_name -> agente
        self.skill_agent_map = {
            # Arquitectura y análisis
            "analyze": "architect",
            "analyze_project": "architect",
            "readme": "architect",
            "migrate_project": "architect",
            "refactor_code": "architect",
            # Generación de código
            "code": "coder",
            "generate_proposal": "coder",
            # Ejecución de comandos y proyectos
            "shell": "executor",
            "docker": "executor",
            "execute_code": "executor",
            "sandbox": "executor",
            "laravel_project": "executor",
            "full_project": "executor",
        }

    def select_agent(self, skill_name: str | None = None) -> Agent:
        """
        Selecciona el agente basado en la skill detectada.
        La detección de skill (regex) está centralizada en IntentAnalyzer.
        """
        if skill_name:
            agent_name = self.skill_agent_map.get(skill_name)
            if agent_name:
                return self.agents[agent_name]

        logger.debug("Sin skill específica, usando agente 'task' por defecto.")
        return self.agents["task"]

    def delegate(
        self,
        task: str,
        context: dict | None = None,
        skill_name: str | None = None,
        skill_params: dict | None = None,
    ) -> str:
        agent = self.select_agent(skill_name)

        logger.info(
            "Delegando al agente: %s (skill: %s)",
            agent.name,
            skill_name or "general",
        )

        return agent.process(
            task=task,
            context=context or {},
            skill_name=skill_name,
            skill_params=skill_params,
        )

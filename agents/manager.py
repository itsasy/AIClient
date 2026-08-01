import logging

from agents.architect import ArchitectAgent
from agents.base import Agent
from agents.coder import CoderAgent
from agents.executor import ExecutorAgent
from agents.multi_turn import MultiTurnAgent
from agents.planner import PlannerAgent
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
            "planner": PlannerAgent(),
        }

        self.skill_agent_map: dict[str, str] = {
            # Arquitectura y análisis
            "analyze": "architect",
            "analyze_project": "architect",
            "readme": "architect",
            "migrate_project": "architect",
            "refactor_code": "architect",
            # Generación de código
            "code": "coder",
            "generate_proposal": "coder",
            # Ejecución
            "shell": "executor",
            "docker": "executor",
            "execute_code": "executor",
            "sandbox": "executor",
            "laravel_project": "executor",
            "full_project": "executor",
            "write_file": "executor",
            # Planificación
            "plan": "planner",
        }

    def select_agent(
        self,
        skill_name: str | None = None,
    ) -> Agent:
        """
        Selecciona el agente basado en la skill detectada.
        La detección de skill está centralizada en IntentAnalyzer.
        """
        if skill_name:
            agent_name = self.skill_agent_map.get(skill_name)

            if agent_name:
                return self.agents.get(
                    agent_name,
                    self.agents["task"],
                )

        logger.debug("Sin skill específica, usando agente 'task' por defecto.")

        return self.agents["task"]

    def delegate(
        self,
        task: str,
        context: dict[str, object] | None = None,
        skill_name: str | None = None,
        skill_params: dict[str, object] | None = None,
    ) -> str:
        agent = self.select_agent(skill_name)

        logger.info(
            "Agente seleccionado: %s",
            agent.name,
        )

        return agent.process(
            task=task,
            context=context if context is not None else {},
            skill_name=skill_name,
            skill_params=skill_params,
        )

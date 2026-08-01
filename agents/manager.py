import logging

from agents.architect import ArchitectAgent
from agents.base import Agent
from agents.coder import CoderAgent
from agents.executor import ExecutorAgent
from agents.multi_turn import MultiTurnAgent
from agents.planner import PlannerAgent
from agents.task_agent import TaskAgent

from core.execution_plan import ExecutionPlan

logger = logging.getLogger(__name__)


class AgentManager:
    """
    Responsable de seleccionar y ejecutar agentes.

    No analiza intención.
    No crea planes.
    No ejecuta skills.
    """

    def __init__(self):

        self.agents: dict[str, Agent] = {
            "architect": ArchitectAgent(),
            "coder": CoderAgent(),
            "executor": ExecutorAgent(),
            "planner": PlannerAgent(),
            "multi_turn": MultiTurnAgent(),
            "task": TaskAgent(),
        }

        self.skill_agent_map: dict[str, str] = {
            # Arquitectura
            "analyze": "architect",
            "analyze_project": "architect",
            "readme": "architect",
            "refactor_code": "architect",
            "migrate_project": "architect",
            # Código
            "code": "coder",
            "generate_proposal": "coder",
            # Ejecución
            "shell": "executor",
            "docker": "executor",
            "execute_code": "executor",
            "sandbox": "executor",
            "write_file": "executor",
            "laravel_project": "executor",
            "full_project": "executor",
            # SDD
            "plan": "planner",
        }

    def select_agent(
        self,
        plan: ExecutionPlan,
    ) -> Agent:
        """
        Selecciona agente basado en el ExecutionPlan.

        Prioridad:

        1. Agente definido explícitamente.
        2. Skill asociada.
        3. Agente task por defecto.
        """

        # -----------------------------------
        # 1. Agente explícito
        # -----------------------------------

        if plan.agent:

            agent = self.agents.get(plan.agent)

            if agent:

                return agent

        # -----------------------------------
        # 2. Resolver por skill
        # -----------------------------------

        if plan.skill:

            agent_name = self.skill_agent_map.get(plan.skill)

            if agent_name:

                return self.agents.get(
                    agent_name,
                    self.agents["task"],
                )

        # -----------------------------------
        # 3. Fallback
        # -----------------------------------

        logger.debug("ExecutionPlan sin agente definido. " "Usando TaskAgent.")

        return self.agents["task"]

    def delegate(
        self,
        plan: ExecutionPlan,
        context: dict | None = None,
    ) -> str:
        """
        Ejecuta el agente seleccionado.
        """

        agent = self.select_agent(plan)

        logger.info(
            "Agente seleccionado: %s",
            agent.name,
        )

        return agent.process(
            plan=plan,
            context=context or {},
        )

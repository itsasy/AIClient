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

    def __init__(self):

        self.agents: dict[str, Agent] = {
            "architect": ArchitectAgent(),
            "coder": CoderAgent(),
            "executor": ExecutorAgent(),
            "planner": PlannerAgent(),
            "multi_turn": MultiTurnAgent(),
            "task": TaskAgent(),
        }

    def delegate(
        self,
        plan: ExecutionPlan,
        context: dict | None = None,
    ) -> str:

        context = context or {}

        agent = self._select(plan)

        logger.info(
            "Agent=%s intent=%s mode=%s",
            agent.name,
            plan.intent,
            plan.execution_mode,
        )

        response = agent.process(
            plan=plan,
            context=context,
        )

        return response

    def _select(
        self,
        plan: ExecutionPlan,
    ) -> Agent:

        if plan.agent:

            return self.agents.get(
                plan.agent,
                self.agents["task"],
            )

        if plan.execution_mode == "multi_step":
            return self.agents["planner"]

        return self.agents["task"]

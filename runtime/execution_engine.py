from __future__ import annotations

import logging
import time
from typing import Any

from core.execution_plan import ExecutionPlan

from core.context.manager import ContextManager

from runtime.agent_runtime import AgentRuntime
from runtime.skill_runtime import SkillRuntime

logger = logging.getLogger(__name__)


class ExecutionEngine:
    """
    Motor principal de ejecución.

    Coordina:

    ExecutionPlan
        |
        v
    Context
        |
        v
    Agent
        |
        v
    Skills
        |
        v
    Resultado


    Responsabilidades:

    - Validar ExecutionPlan.
    - Construir contexto.
    - Ejecutar agente.
    - Ejecutar skills cuando corresponda.
    - Registrar métricas.
    - Manejar errores.


    No:

    - Analiza intención.
    - Construye planes.
    - Genera prompts.
    - Selecciona LLM.
    """

    def __init__(
        self,
        context_manager: ContextManager | None = None,
        agent_runtime: AgentRuntime | None = None,
        skill_runtime: SkillRuntime | None = None,
    ):

        self.context_manager = context_manager or ContextManager()

        self.agent_runtime = agent_runtime or AgentRuntime()

        self.skill_runtime = skill_runtime or SkillRuntime()

        self.metrics = {
            "executions": 0,
            "success": 0,
            "failed": 0,
            "total_time": 0,
        }

    # ==========================================================
    # Public API
    # ==========================================================

    def execute(
        self,
        plan: ExecutionPlan,
    ) -> dict[str, Any]:

        start = time.time()

        logger.info(
            "Execution started | id=%s intent=%s",
            plan.id,
            plan.intent,
        )

        try:

            errors = plan.validate()

            if errors:

                logger.warning(
                    "ExecutionPlan con errores: %s",
                    errors,
                )

            plan.mark_running()

            # --------------------------------------------------
            # Context
            # --------------------------------------------------

            context = self.context_manager.build(
                plan,
            )

            plan.execution_context = context

            # --------------------------------------------------
            # Agent
            # --------------------------------------------------

            result = self.agent_runtime.execute(
                plan,
                context,
            )

            # --------------------------------------------------
            # Optional skills
            # --------------------------------------------------

            if plan.metadata.get("execute_skills", False):

                skill_result = self.skill_runtime.execute(
                    plan,
                    context,
                )

                result = {
                    "agent": result,
                    "skill": skill_result,
                }

            plan.mark_completed(
                result,
            )

            self.metrics["success"] += 1

            return {
                "ok": True,
                "plan_id": plan.id,
                "result": result,
            }

        except Exception as e:

            self.metrics["failed"] += 1

            logger.exception(
                "Execution failed",
            )

            plan.mark_failed(
                str(e),
            )

            return {
                "ok": False,
                "plan_id": plan.id,
                "error": str(e),
            }

        finally:

            elapsed = time.time() - start

            self.metrics["executions"] += 1

            self.metrics["total_time"] += elapsed

            logger.info(
                "Execution finished %.3fs",
                elapsed,
            )

    # ==========================================================
    # Debug
    # ==========================================================

    def get_metrics(
        self,
    ) -> dict[str, Any]:

        return self.metrics.copy()

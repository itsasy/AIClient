from __future__ import annotations

import logging
from typing import Any, Callable

from core.execution_plan import ExecutionPlan
from core.execution_result import ExecutionResult
from core.execution_step import ExecutionStep
from core.governance.capability_guard import (
    CapabilityError,
    CapabilityGuard,
)

from runtime.registry.agent_registry import AgentRegistry
from runtime.registry.skill_registry import SkillRegistry

logger = logging.getLogger(__name__)


class UnitDispatcher:
    """
    Resuelve y ejecuta una unidad declarada en un ExecutionPlan.

    Responsabilidades:

        - Resolver Agents y Skills registrados.
        - Verificar capabilities declaradas por Skills.
        - Invocar su contrato de ejecución.
        - Normalizar resultados de ejecución.
        - Normalizar errores de dispatch.
        - Añadir metadata de dispatch.

    No:

        - Decide qué unidad debe ejecutarse.
        - Construye ExecutionPlans.
        - Gestiona lifecycle del plan.
        - Gestiona retries.
        - Evalúa resultados.
        - Ejecuta learning.
        - Registra Agents o Skills.
    """

    name = "dispatcher"

    def __init__(
        self,
        agent_registry: AgentRegistry,
        skill_registry: SkillRegistry,
        capability_guard: CapabilityGuard | None = None,
    ) -> None:
        if agent_registry is None:
            raise ValueError(
                "agent_registry no puede ser None.",
            )

        if skill_registry is None:
            raise ValueError(
                "skill_registry no puede ser None.",
            )

        self.agent_registry = agent_registry
        self.skill_registry = skill_registry
        self.capability_guard = (
            capability_guard if capability_guard is not None else CapabilityGuard()
        )

    # ==========================================================
    # Public API
    # ==========================================================

    def dispatch(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any],
    ) -> ExecutionResult:
        """
        Resuelve y ejecuta una unidad.

        Para Skills, se realiza una pre-verificación centralizada
        de las capabilities declaradas antes de invocar la Skill.

        El Dispatcher no modifica el plan ni decide el flujo
        posterior de ejecución.
        """

        if not isinstance(
            plan,
            ExecutionPlan,
        ):
            raise TypeError(
                "plan debe ser un ExecutionPlan.",
            )

        if not isinstance(
            step,
            ExecutionStep,
        ):
            raise TypeError(
                "step debe ser un ExecutionStep.",
            )

        if not isinstance(
            context,
            dict,
        ):
            raise TypeError(
                "context debe ser un diccionario.",
            )

        unit_type = step.unit_type
        unit_name = step.unit_name

        if unit_type == "agent":
            return self._dispatch_agent(
                plan=plan,
                step=step,
                context=context,
            )

        if unit_type == "skill":
            return self._dispatch_skill(
                plan=plan,
                step=step,
                context=context,
            )

        return self._failure(
            plan=plan,
            step=step,
            error=f"Tipo de unidad inválido: {unit_type}",
        )

    # ==========================================================
    # Agent
    # ==========================================================

    def _dispatch_agent(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any],
    ) -> ExecutionResult:

        agent = self._resolve(
            registry=self.agent_registry,
            unit_name=step.unit_name,
        )

        if agent is None:
            return self._failure(
                plan=plan,
                step=step,
                error=f"Agent no encontrado: {step.unit_name}",
            )

        return self._invoke(
            plan=plan,
            step=step,
            context=context,
            executor=f"agent:{step.unit_name}",
            callback=lambda: agent.process(
                plan,
                step,
                context,
            ),
        )

    # ==========================================================
    # Skill
    # ==========================================================

    def _dispatch_skill(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any],
    ) -> ExecutionResult:

        skill = self._resolve(
            registry=self.skill_registry,
            unit_name=step.unit_name,
        )

        if skill is None:
            return self._failure(
                plan=plan,
                step=step,
                error=f"Skill no encontrada: {step.unit_name}",
            )

        # ------------------------------------------------------
        # Capability pre-check
        # ------------------------------------------------------
        #
        # Se verifica ANTES de skill.execute().
        #
        # Esto crea una barrera centralizada para todas las
        # Skills que declaren capabilities sensibles.
        #

        capability_error = self._check_skill_capabilities(
            plan=plan,
            step=step,
            skill=skill,
        )

        if capability_error is not None:
            return self._failure(
                plan=plan,
                step=step,
                error=capability_error,
                executor=f"skill:{step.unit_name}",
            )

        # ------------------------------------------------------
        # Ejecución de la Skill
        # ------------------------------------------------------

        return self._invoke(
            plan=plan,
            step=step,
            context=context,
            executor=f"skill:{step.unit_name}",
            callback=lambda: skill.execute(
                plan,
                step,
                context,
            ),
        )

    # ==========================================================
    # Capability Guard
    # ==========================================================

    def _check_skill_capabilities(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        skill: Any,
    ) -> str | None:
        """
        Verifica las capabilities declaradas por una Skill.

        La Skill declara, por ejemplo:

            capabilities = ("file_write",)

        El Dispatcher traduce esas capabilities a las
        comprobaciones correspondientes del CapabilityGuard.

        Si alguna capability no está permitida, se devuelve
        el error y la Skill no llega a ejecutarse.

        Capabilities actualmente soportadas:

            file_write
            file_delete
            shell
            network
            sudo

        Las capabilities desconocidas no se bloquean aquí:
        quedan fuera del mapping de este guard y pueden ser
        gestionadas por una política posterior.
        """

        capabilities = (
            getattr(
                skill,
                "capabilities",
                (),
            )
            or ()
        )

        if isinstance(
            capabilities,
            str,
        ):
            capabilities = (capabilities,)

        guard = self.capability_guard

        try:
            for capability in capabilities:
                if capability in {
                    "file_write",
                    "file_delete",
                }:
                    guard.require_write(
                        plan,
                        actor=step.unit_name,
                    )

                elif capability == "shell":
                    guard.require_shell(
                        plan,
                        actor=step.unit_name,
                    )

                elif capability == "network":
                    guard.require_network(
                        plan,
                        actor=step.unit_name,
                    )

                elif capability == "sudo":
                    guard.require_sudo(
                        plan,
                        actor=step.unit_name,
                    )

        except CapabilityError as exc:
            logger.warning(
                "Capability bloqueada | " "plan=%s | skill=%s | capabilities=%s | error=%s",
                plan.id,
                step.unit_name,
                capabilities,
                exc,
            )

            return str(exc)

        return None

    # ==========================================================
    # Resolution
    # ==========================================================

    @staticmethod
    def _resolve(
        registry: Any,
        unit_name: str,
    ) -> Any | None:
        """
        Resuelve una unidad desde su registry.

        El Dispatcher conoce el contrato mínimo del registry:
        get(name) -> unidad | None.
        """

        try:
            return registry.get(
                unit_name,
            )

        except Exception:
            logger.exception(
                "Error resolviendo unidad=%s",
                unit_name,
            )

            return None

    # ==========================================================
    # Invocation
    # ==========================================================

    def _invoke(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any],
        executor: str,
        callback: Callable[[], Any],
    ) -> ExecutionResult:
        """
        Invoca una unidad y normaliza su resultado.

        Si la unidad ya devuelve ExecutionResult, se preserva
        su estado y se complementa su metadata.

        Si devuelve un valor normal, se transforma en success.

        Si lanza una excepción, se transforma en failure.
        """

        try:
            raw_result = callback()

            if isinstance(
                raw_result,
                ExecutionResult,
            ):
                return self._normalize_result(
                    plan=plan,
                    step=step,
                    result=raw_result,
                    executor=executor,
                )

            return ExecutionResult.success(
                plan_id=plan.id,
                result=raw_result,
                executor=executor,
                metadata=self._metadata(
                    step=step,
                    executor=executor,
                ),
            )

        except Exception as exc:
            logger.exception(
                "Error ejecutando unidad=%s",
                executor,
            )

            return self._failure(
                plan=plan,
                step=step,
                error=str(exc),
                executor=executor,
            )

    # ==========================================================
    # Result normalization
    # ==========================================================

    def _normalize_result(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        result: ExecutionResult,
        executor: str,
    ) -> ExecutionResult:
        """
        Conserva el ExecutionResult generado por la unidad.

        El Dispatcher únicamente completa metadata de dispatch;
        no transforma el estado de ejecución.
        """

        result.plan_id = plan.id

        result.metadata.update(
            self._metadata(
                step=step,
                executor=executor,
            )
        )

        return result

    # ==========================================================
    # Result helpers
    # ==========================================================

    def _failure(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        error: str,
        executor: str | None = None,
    ) -> ExecutionResult:

        executor_name = executor or self.name

        return ExecutionResult.fail(
            plan_id=plan.id,
            error=error,
            executor=executor_name,
            metadata=self._metadata(
                step=step,
                executor=executor_name,
            ),
        )

    @staticmethod
    def _metadata(
        step: ExecutionStep,
        executor: str,
    ) -> dict[str, Any]:
        return {
            "step_id": step.id,
            "unit_type": step.unit_type,
            "unit_name": step.unit_name,
            "executor": executor,
        }

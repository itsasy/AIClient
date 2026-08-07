from __future__ import annotations

import logging
import time
from typing import Any

from core.execution_plan import ExecutionPlan
from core.execution_result import ExecutionResult
from core.execution_step import ExecutionStep
from core.context.manager import ContextManager
from core.intent import IntentAnalyzer
from core.planning import PlanBuilder

from runtime.dispatcher import UnitDispatcher
from runtime.registry.agent_registry import AgentRegistry
from runtime.registry.skill_registry import SkillRegistry

from skills.loader import SkillLoader
from agents.loader import AgentLoader

logger = logging.getLogger(__name__)


class ExecutionEngine:
    """
    Único dueño del lifecycle de ejecución.

    Coordina las etapas, no las implementa.

    Flujo:

        User input
            ↓
        IntentAnalyzer
            ↓
        PlanBuilder
            ↓
        ExecutionPlan
            ↓
        validate
            ↓
        context
            ↓
        execute
            ↓
        evaluate
            ↓
        retry
            ↓
        learn
            ↓
        finalize
            ↓
        ExecutionResult

    En un plan multi-step, el resultado de cada step se incorpora
    al execution context antes de ejecutar los steps dependientes.
    """

    name = "execution_engine"

    def __init__(
        self,
        agent_registry: AgentRegistry | None = None,
        skill_registry: SkillRegistry | None = None,
        context_manager: ContextManager | None = None,
        intent_analyzer: IntentAnalyzer | None = None,
        plan_builder: PlanBuilder | None = None,
    ):
        # ==========================================================
        # Core dependencies
        # ==========================================================

        self.context_manager = context_manager or ContextManager()

        self.intent_analyzer = intent_analyzer or IntentAnalyzer()

        self.plan_builder = plan_builder or PlanBuilder()

        # ==========================================================
        # Registries
        # ==========================================================

        self.agent_registry = agent_registry or AgentRegistry()

        self.skill_registry = skill_registry or SkillRegistry()

        # ==========================================================
        # Agent loading
        # ==========================================================

        self.agent_loader = AgentLoader(
            self.agent_registry,
        )

        self.agent_loader.load_defaults()

        logger.info(
            "Agents cargados=%s",
            self.agent_registry.list(),
        )

        # ==========================================================
        # Skill loading
        # ==========================================================

        self.skill_loader = SkillLoader(
            self.skill_registry,
        )

        self.skill_loader.load_defaults()

        logger.info(
            "Skills cargadas=%s",
            self.skill_registry.list(),
        )

        # ==========================================================
        # Dispatcher
        # ==========================================================

        self.dispatcher = UnitDispatcher(
            agent_registry=self.agent_registry,
            skill_registry=self.skill_registry,
        )

        # ==========================================================
        # Metrics
        # ==========================================================

        self.metrics = {
            "executions": 0,
            "success": 0,
            "partial": 0,
            "failed": 0,
            "cancelled": 0,
            "retries": 0,
        }

        # ==========================================================
        # Self-Critic
        # ==========================================================

        try:
            from core.self_critic import SelfCritic

            self.critic = SelfCritic()

        except ImportError:
            logger.warning(
                "SelfCritic no disponible",
            )

            self.critic = None

        # ==========================================================
        # Continuous Learning
        # ==========================================================

        try:
            from core.learner import ContinuousLearner

            self.learner = ContinuousLearner()

        except ImportError:
            logger.warning(
                "ContinuousLearner no disponible",
            )

            self.learner = None

    # ==========================================================
    # Public API
    # ==========================================================

    def execute_from_input(
        self,
        user_input: str,
        metadata: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        logger.info(
            "Engine: procesando entrada: %s",
            user_input[:100],
        )

        intent = self.intent_analyzer.analyze(
            user_input,
        )

        plan = self.plan_builder.build(
            intent=intent,
            original_task=user_input,
        )

        if metadata:
            plan.metadata.update(
                metadata,
            )

        return self.execute(plan)

    def execute(
        self,
        plan: ExecutionPlan,
    ) -> ExecutionResult:
        started = time.monotonic()

        self.metrics["executions"] += 1

        try:
            # --------------------------------------------------
            # 1. Validación
            # --------------------------------------------------

            errors = plan.validate()

            if errors:
                return self._fail(
                    plan,
                    "; ".join(errors),
                )

            plan.mark_validated()

            # --------------------------------------------------
            # 2. Contexto inicial
            # --------------------------------------------------

            context = self.context_manager.build(plan) or {}

            plan.loaded_context = dict(
                context,
            )

            # Crear espacio explícito para resultados de ejecución.
            self._initialize_execution_context(
                plan,
                context,
            )

            plan.mark_running()

            # --------------------------------------------------
            # 3. Ejecución + evaluación + retries
            # --------------------------------------------------

            result = self._execute_with_retries(
                plan,
                context,
            )

            # --------------------------------------------------
            # 4. Metadatos finales
            # --------------------------------------------------

            duration = round(
                time.monotonic() - started,
                3,
            )

            result.metadata.update(
                {
                    "engine": self.name,
                    "duration": duration,
                    "plan_id": plan.id,
                }
            )

            # --------------------------------------------------
            # 5. Aprendizaje
            # --------------------------------------------------

            self._learn(
                plan,
                result,
            )

            # --------------------------------------------------
            # 6. Estado final
            # --------------------------------------------------

            self._apply_plan_state(
                plan,
                result,
            )

            self._update_metrics(
                result,
            )

            return result

        except Exception as exc:
            logger.exception(
                "Engine error",
            )

            try:
                plan.mark_failed()

            except Exception:
                pass

            return self._fail(
                plan,
                str(exc),
            )

    # ==========================================================
    # Execution context
    # ==========================================================

    def _initialize_execution_context(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
    ) -> None:
        """
        Inicializa el espacio donde se almacenan los resultados
        de los steps.

        El contexto original sigue siendo responsabilidad del
        ContextManager.

        El bloque "execution" pertenece exclusivamente al
        ExecutionEngine.
        """

        execution = context.setdefault(
            "execution",
            {},
        )

        execution.setdefault(
            "plan_id",
            plan.id,
        )

        execution.setdefault(
            "task",
            plan.original_task,
        )

        execution.setdefault(
            "steps",
            {},
        )

        plan.execution_context = execution

    def _store_step_result(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
        step: ExecutionStep,
        result: ExecutionResult,
    ) -> None:
        """
        Persiste el resultado de un step dentro del contexto
        de ejecución.

        Esto permite que steps posteriores consuman resultados
        producidos por sus dependencias.
        """

        execution = context.setdefault(
            "execution",
            {},
        )

        steps = execution.setdefault(
            "steps",
            {},
        )

        steps[step.id] = {
            "id": step.id,
            "description": step.description,
            "unit_type": step.unit_type,
            "unit_name": step.unit_name,
            "status": result.status,
            "result": result.result,
            "error": result.error,
            "metadata": dict(result.metadata),
        }

        # Mantener el resultado también en el propio step.
        if result.is_success:
            step.mark_completed(
                result.result,
            )

        elif result.is_failure:
            step.mark_failed(
                result.error or "Error desconocido",
            )

        plan.execution_context = execution

    def _build_step_context(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
        step: ExecutionStep,
    ) -> dict[str, Any]:
        """
        Construye el contexto que recibe una unidad ejecutable.

        Además del contexto global, expone explícitamente los
        resultados de las dependencias del step.
        """

        step_context = dict(
            context,
        )

        execution = context.get(
            "execution",
            {},
        )

        all_steps = execution.get(
            "steps",
            {},
        )

        dependencies: dict[str, Any] = {}

        for dependency_id in step.depends_on:
            dependency = all_steps.get(
                dependency_id,
            )

            if dependency is not None:
                dependencies[dependency_id] = dependency

        step_context["execution"] = dict(
            execution,
        )

        step_context["execution"]["current_step"] = {
            "id": step.id,
            "description": step.description,
            "unit_type": step.unit_type,
            "unit_name": step.unit_name,
            "params": dict(step.params),
        }

        step_context["execution"]["dependencies"] = dependencies

        return step_context

    # ==========================================================
    # Execution with retries
    # ==========================================================

    def _execute_with_retries(
        self,
        plan: ExecutionPlan,
        context: dict,
    ) -> ExecutionResult:
        """
        Ejecuta el plan con reintentos controlados.

        La evaluación ocurre sobre el resultado completo del plan,
        no sobre cada step individual.
        """

        max_retries = plan.metadata.get(
            "max_retries",
            plan.max_retries,
        )

        retries = 0
        last_result: ExecutionResult | None = None

        while retries <= max_retries:
            # --------------------------------------------------
            # Ejecutar
            # --------------------------------------------------

            if plan.is_multi_step():
                result = self._execute_steps(
                    plan,
                    context,
                )

            else:
                result = self._execute_single(
                    plan,
                    context,
                )

            # --------------------------------------------------
            # Evaluar
            # --------------------------------------------------

            result = self._evaluate(
                plan,
                result,
            )

            # --------------------------------------------------
            # Éxito
            # --------------------------------------------------

            if result.is_success or result.is_partial:
                return result

            # --------------------------------------------------
            # Retry
            # --------------------------------------------------

            if result.is_failure and retries < max_retries:
                retries += 1

                self.metrics["retries"] += 1

                logger.info(
                    "Reintentando plan %s " "(intento %d/%d)",
                    plan.id,
                    retries,
                    max_retries,
                )

                result.metadata["retry_count"] = retries

                last_result = result

                # Reiniciar resultados de ejecución para que
                # el retry empiece desde un estado coherente.
                self._reset_execution_context(
                    plan,
                    context,
                )

                time.sleep(0.5)

                continue

            return result

        return last_result or ExecutionResult.fail(
            plan_id=plan.id,
            error="Se agotaron los reintentos",
            executor=self.name,
        )

    def _reset_execution_context(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
    ) -> None:
        execution = context.setdefault(
            "execution",
            {},
        )

        execution["steps"] = {}

        plan.execution_context = execution

        for step in plan.steps:
            step.status = "pending"
            step.result = None
            step.error = None

    # ==========================================================
    # Single execution
    # ==========================================================

    def _execute_single(
        self,
        plan: ExecutionPlan,
        context: dict,
    ) -> ExecutionResult:
        if not plan.execution_unit_type or not plan.execution_unit:
            return self._fail(
                plan,
                "Plan sin unidad de ejecución.",
            )

        step = ExecutionStep(
            description=(plan.objective or plan.original_task),
            unit_type=plan.execution_unit_type,
            unit_name=plan.execution_unit,
            params=plan.params,
        )

        step_context = self._build_step_context(
            plan,
            context,
            step,
        )

        result = self.dispatcher.dispatch(
            plan,
            step,
            step_context,
        )

        self._store_step_result(
            plan,
            context,
            step,
            result,
        )

        return result

    # ==========================================================
    # Multi-step execution
    # ==========================================================

    def _execute_steps(
        self,
        plan: ExecutionPlan,
        context: dict,
    ) -> ExecutionResult:
        if not plan.steps:
            return self._fail(
                plan,
                "Plan multi_step sin pasos.",
            )

        ordered = self._resolve_order(
            plan.steps,
        )

        results: list[ExecutionResult] = []
        errors: list[dict[str, str]] = []

        for step in ordered:
            logger.info(
                "Ejecutando step %s (%s:%s)",
                step.description,
                step.unit_type,
                step.unit_name,
            )

            # --------------------------------------------------
            # Dependencias
            # --------------------------------------------------

            dependency_failure = self._dependency_failure(
                step,
                plan,
                context,
            )

            if dependency_failure is not None:
                logger.error(
                    "Step '%s' omitido: %s",
                    step.description,
                    dependency_failure,
                )

                step.mark_skipped(
                    dependency_failure,
                )

                result = ExecutionResult.fail(
                    plan_id=plan.id,
                    error=dependency_failure,
                    executor=self.name,
                    metadata={
                        "step_id": step.id,
                        "step": step.description,
                        "unit": step.unit_name,
                    },
                )

                self._store_step_result(
                    plan,
                    context,
                    step,
                    result,
                )

                results.append(
                    result,
                )

                errors.append(
                    {
                        "step": step.description,
                        "unit": step.unit_name,
                        "error": dependency_failure,
                    }
                )

                if plan.stop_on_error:
                    break

                continue

            # --------------------------------------------------
            # Contexto específico del step
            # --------------------------------------------------

            step_context = self._build_step_context(
                plan,
                context,
                step,
            )

            # --------------------------------------------------
            # Ejecución
            # --------------------------------------------------

            step.mark_running()

            result = self.dispatcher.dispatch(
                plan,
                step,
                step_context,
            )

            self._store_step_result(
                plan,
                context,
                step,
                result,
            )

            results.append(
                result,
            )

            # --------------------------------------------------
            # Error
            # --------------------------------------------------

            if result.is_failure:
                error = result.error or "Error desconocido"

                logger.error(
                    "Step '%s' falló: %s",
                    step.description,
                    error,
                )

                errors.append(
                    {
                        "step": step.description,
                        "unit": step.unit_name,
                        "error": error,
                    }
                )

                if plan.stop_on_error:
                    break

        # ------------------------------------------------------
        # Resultado final
        # ------------------------------------------------------

        result_payload = [
            {
                "step_id": step.id,
                "description": step.description,
                "unit_type": step.unit_type,
                "unit_name": step.unit_name,
                "status": result.status,
                "result": result.result,
                "error": result.error,
            }
            for step, result in zip(
                [
                    step
                    for step in ordered
                    if step.status != "skipped"
                    or step.id
                    in context.get(
                        "execution",
                        {},
                    ).get(
                        "steps",
                        {},
                    )
                ],
                results,
            )
        ]

        # ------------------------------------------------------
        # Éxito completo
        # ------------------------------------------------------

        if not errors:
            final_result = results[-1].result if results else None

            return ExecutionResult.success(
                plan_id=plan.id,
                result=final_result,
                executor=self.name,
                metadata={
                    "steps": result_payload,
                    "step_count": len(results),
                },
            )

        # ------------------------------------------------------
        # Fallo completo
        # ------------------------------------------------------

        if len(errors) == len(results):
            detail = "\n".join(
                f"- {error['step']} " f"({error['unit']}): " f"{error['error']}" for error in errors
            )

            return ExecutionResult.fail(
                plan_id=plan.id,
                error=detail,
                executor=self.name,
                metadata={
                    "steps": result_payload,
                },
            )

        # ------------------------------------------------------
        # Ejecución parcial
        # ------------------------------------------------------

        detail = "\n".join(
            f"- {error['step']} " f"({error['unit']}): " f"{error['error']}" for error in errors
        )

        return ExecutionResult.partial(
            plan_id=plan.id,
            result=(results[-1].result if results else None),
            error=detail,
            executor=self.name,
            metadata={
                "steps": result_payload,
            },
        )

    # ==========================================================
    # Dependency validation
    # ==========================================================

    def _dependency_failure(
        self,
        step: ExecutionStep,
        plan: ExecutionPlan,
        context: dict[str, Any],
    ) -> str | None:
        if not step.depends_on:
            return None

        execution = context.get(
            "execution",
            {},
        )

        completed_steps = execution.get(
            "steps",
            {},
        )

        for dependency_id in step.depends_on:
            dependency = completed_steps.get(
                dependency_id,
            )

            if dependency is None:
                return f"Dependencia no ejecutada: " f"{dependency_id}"

            if dependency.get("status") != "completed":
                return f"Dependencia fallida: " f"{dependency_id}"

        return None

    # ==========================================================
    # Evaluation
    # ==========================================================

    def _evaluate(
        self,
        plan: ExecutionPlan,
        result: ExecutionResult,
    ) -> ExecutionResult:
        """
        Etapa de evaluación post-ejecución.
        """

        if not plan.metadata.get(
            "requires_self_critic",
            False,
        ):
            return result

        if result.is_failure:
            return result

        if self.critic is None:
            return result

        try:
            evaluation = self.critic.evaluate(
                plan,
                result,
            )

            if evaluation.get(
                "pass",
                True,
            ):
                return result

            return ExecutionResult.retry(
                plan_id=plan.id,
                error=evaluation.get(
                    "reason",
                    "Evaluación fallida",
                ),
                retries=result.retries + 1,
                executor="self_critic",
            )

        except Exception as exc:
            logger.warning(
                "SelfCritic falló: %s",
                exc,
            )

            return result

    # ==========================================================
    # Learning
    # ==========================================================

    def _learn(
        self,
        plan: ExecutionPlan,
        result: ExecutionResult,
    ) -> None:
        """
        Aprendizaje continuo post-ejecución.

        No debe bloquear la respuesta principal.
        """

        if self.learner is None:
            return

        if not result.is_success and not result.is_partial:
            return

        try:
            self.learner.extract_and_learn(
                user_query=plan.original_task,
                assistant_response=str(
                    result.result or result.error or "",
                ),
            )

        except Exception as exc:
            logger.debug(
                "Aprendizaje continuo falló: %s",
                exc,
            )

    # ==========================================================
    # Helpers
    # ==========================================================

    def _resolve_order(
        self,
        steps: list[ExecutionStep],
    ) -> list[ExecutionStep]:
        ordered: list[ExecutionStep] = []

        resolved: set[str] = set()

        pending = list(steps)

        available_ids = {step.id for step in steps}

        while pending:
            progress = False

            for step in pending[:]:
                missing = [dep for dep in step.depends_on if dep not in available_ids]

                if missing:
                    raise ValueError(
                        f"Dependencias inexistentes: {missing}",
                    )

                if all(dep in resolved for dep in step.depends_on):
                    ordered.append(
                        step,
                    )

                    resolved.add(
                        step.id,
                    )

                    pending.remove(
                        step,
                    )

                    progress = True

            if not progress:
                raise RuntimeError(
                    "Dependencias circulares en el plan.",
                )

        return ordered

    def _apply_plan_state(
        self,
        plan: ExecutionPlan,
        result: ExecutionResult,
    ) -> None:
        if result.is_success:
            plan.mark_completed()

        elif result.is_partial:
            plan.mark_partial()

        elif result.is_failure:
            plan.mark_failed()

        elif result.is_cancelled:
            plan.mark_cancelled()

    def _update_metrics(
        self,
        result: ExecutionResult,
    ) -> None:
        if result.is_success:
            self.metrics["success"] += 1

        elif result.is_partial:
            self.metrics["partial"] += 1

        elif result.is_failure:
            self.metrics["failed"] += 1

        elif result.is_cancelled:
            self.metrics["cancelled"] += 1

        elif result.is_retry:
            self.metrics["retries"] += 1

    def _fail(
        self,
        plan: ExecutionPlan,
        error: str,
    ) -> ExecutionResult:
        logger.error(
            "Plan %s falló: %s",
            plan.id,
            error,
        )

        return ExecutionResult.fail(
            plan_id=plan.id,
            error=error,
            executor=self.name,
        )

    def get_metrics(
        self,
    ) -> dict[str, Any]:
        return self.metrics.copy()

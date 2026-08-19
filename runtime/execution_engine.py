from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.analytics.metrics_store import MetricsStore
from core.analytics.models import ExecutionMetric
from core.context.manager import ContextManager
from core.engram_memory import EngramMemory
from core.execution_plan import ExecutionPlan
from core.execution_result import ExecutionResult
from core.execution_step import ExecutionStep
from core.intent import IntentAnalyzer
from core.learner import ContinuousLearner
from core.planning import PlanBuilder
from core.self_critic import SelfCritic
from runtime.dispatcher import UnitDispatcher
from runtime.registry.agent_registry import AgentRegistry
from runtime.registry.skill_registry import SkillRegistry

logger = logging.getLogger(__name__)


class ExecutionEngine:
    """
    Único dueño del lifecycle de ejecución.

    El ExecutionEngine ejecuta planes utilizando los registries
    proporcionados por la composición de la aplicación.

    No:

        - Carga Agents.
        - Carga Skills.
        - Gestiona AgentManager.
        - Gestiona SkillManager.
        - Decide cómo se descubren o registran unidades.

    Flujo oficial:

        user input
            ↓
        IntentAnalyzer
            ↓
        IntentResult
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
        finalize
            ↓
        learning

    ExecutionResult es la fuente de verdad del lifecycle.

    El engine utiliza:

        result.is_success
        result.is_partial
        result.is_failure
        result.is_retry
        result.is_cancelled
        result.is_terminal

    result.status se reserva para:

        - serialización
        - logging
        - métricas
        - compatibilidad con datos legacy
    """

    name = "execution_engine"

    def __init__(
        self,
        agent_registry: AgentRegistry,
        skill_registry: SkillRegistry,
        context_manager: ContextManager | None = None,
        intent_analyzer: IntentAnalyzer | None = None,
        plan_builder: PlanBuilder | None = None,
        command_router: Any | None = None,
    ) -> None:
        if agent_registry is None:
            raise ValueError(
                "ExecutionEngine requiere agent_registry.",
            )

        if skill_registry is None:
            raise ValueError(
                "ExecutionEngine requiere skill_registry.",
            )

        self.agent_registry = agent_registry
        self.skill_registry = skill_registry

        self.context_manager = context_manager if context_manager is not None else ContextManager()

        self.intent_analyzer = intent_analyzer if intent_analyzer is not None else IntentAnalyzer()

        self.plan_builder = plan_builder if plan_builder is not None else PlanBuilder()

        self.command_router = command_router

        self.dispatcher = UnitDispatcher(
            agent_registry=self.agent_registry,
            skill_registry=self.skill_registry,
        )

        self.metrics: dict[str, int] = {
            "executions": 0,
            "success": 0,
            "partial": 0,
            "failed": 0,
            "cancelled": 0,
            "retries": 0,
        }

        self.critic = SelfCritic()
        self.learner = ContinuousLearner()
        self.engram = EngramMemory()
        self.metrics_store = MetricsStore()

        self._retry_context: dict[str, dict[str, Any]] = {}

        logger.info(
            "ExecutionEngine inicializado | agents=%s | skills=%s",
            self.agent_registry.list(),
            self.skill_registry.list(),
        )

    # =========================================================
    # Public API
    # =========================================================

    def execute_from_input(
        self,
        user_input: str,
        metadata: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        if not user_input or not user_input.strip():
            raise ValueError(
                "user_input no puede estar vacío.",
            )

        logger.info(
            "Engine procesando entrada=%s",
            user_input[:100],
        )

        # -----------------------------------------------------
        # Slash commands
        # -----------------------------------------------------

        if self.command_router is not None:
            try:
                slash_plan = self.command_router.process(
                    user_input,
                )
            except ValueError as exc:
                return ExecutionResult.fail(
                    plan_id="slash",
                    error=str(exc),
                    executor=self.name,
                )

            if slash_plan is not None:
                if metadata:
                    slash_plan.metadata.update(metadata)

                return self.execute(
                    slash_plan,
                )

        # -----------------------------------------------------
        # Intent → Plan
        # -----------------------------------------------------

        intent = self.intent_analyzer.analyze(
            user_input,
        )

        plan = self.plan_builder.build(
            intent=intent,
            original_task=user_input,
        )

        if metadata:
            plan.metadata.update(metadata)

        return self.execute(
            plan,
        )

    def execute(
        self,
        plan: ExecutionPlan,
    ) -> ExecutionResult:
        if plan is None:
            raise ValueError(
                "ExecutionEngine.execute requiere un plan.",
            )

        started_monotonic = time.monotonic()
        started_at = datetime.now(timezone.utc)

        self.metrics["executions"] += 1

        try:
            # -------------------------------------------------
            # Validation
            # -------------------------------------------------

            errors = plan.validate()

            if errors:
                result = self._fail(
                    plan,
                    "; ".join(errors),
                )

                return self._finalize(
                    plan=plan,
                    result=result,
                    started_monotonic=started_monotonic,
                    started_at=started_at,
                )

            plan.mark_validated()

            # -------------------------------------------------
            # Context
            # -------------------------------------------------

            context = self.context_manager.build(plan) or {}

            plan.loaded_context = dict(context)

            plan.mark_running()

            # -------------------------------------------------
            # Execution + retry + evaluation
            # -------------------------------------------------

            result = self._execute_with_retries(
                plan,
                context,
                started_at=started_at,
            )

            # -------------------------------------------------
            # Finalization
            # -------------------------------------------------

            result = self._finalize(
                plan=plan,
                result=result,
                started_monotonic=started_monotonic,
                started_at=started_at,
            )

            # -------------------------------------------------
            # Learning
            # -------------------------------------------------

            self._learn(
                plan,
                result,
            )

            return result

        except Exception as exc:
            logger.exception(
                "Error fatal en ExecutionEngine",
            )

            try:
                plan.mark_failed()
            except Exception:
                logger.exception(
                    "No se pudo marcar plan como failed",
                )

            result = self._fail(
                plan,
                str(exc),
            )

            return self._finalize(
                plan=plan,
                result=result,
                started_monotonic=started_monotonic,
                started_at=started_at,
            )

    # =========================================================
    # ExecutionResult helpers
    # =========================================================

    @staticmethod
    def _result_is_success(
        result: ExecutionResult | Any,
    ) -> bool:
        return isinstance(result, ExecutionResult) and result.is_success

    @staticmethod
    def _result_is_partial(
        result: ExecutionResult | Any,
    ) -> bool:
        return isinstance(result, ExecutionResult) and result.is_partial

    @staticmethod
    def _result_is_failure(
        result: ExecutionResult | Any,
    ) -> bool:
        return isinstance(result, ExecutionResult) and result.is_failure

    @staticmethod
    def _result_is_retry(
        result: ExecutionResult | Any,
    ) -> bool:
        return isinstance(result, ExecutionResult) and result.is_retry

    @staticmethod
    def _result_is_cancelled(
        result: ExecutionResult | Any,
    ) -> bool:
        return isinstance(result, ExecutionResult) and result.is_cancelled

    @staticmethod
    def _result_is_terminal(
        result: ExecutionResult | Any,
    ) -> bool:
        return isinstance(result, ExecutionResult) and result.is_terminal

    @staticmethod
    def _legacy_status_is_success(
        value: Any,
    ) -> bool:
        """
        Compatibilidad exclusiva con datos legacy que todavía
        estén almacenados como dict.

        El lifecycle nuevo NO utiliza esta función para
        ExecutionResult.
        """
        return value in {
            "completed",
            "success",
            "ok",
        }

    @classmethod
    def _dependency_result_is_success(
        cls,
        value: Any,
    ) -> bool:
        if isinstance(value, ExecutionResult):
            return value.is_success

        if isinstance(value, dict):
            status = value.get("status")

            if cls._legacy_status_is_success(status):
                return True

            raw = value.get("result")

            if isinstance(
                raw,
                ExecutionResult,
            ):
                return raw.is_success

            if isinstance(raw, dict) and "ok" in raw:
                return bool(raw.get("ok"))

        return False

    # =========================================================
    # Finalization
    # =========================================================

    def _finalize(
        self,
        plan: ExecutionPlan,
        result: ExecutionResult,
        started_monotonic: float,
        started_at: datetime,
    ) -> ExecutionResult:
        """
        Único punto de finalización pública.

        Garantía:

            nunca devuelve status="retry".

        ExecutionResult es la fuente de verdad.
        """

        if not isinstance(
            result,
            ExecutionResult,
        ):
            logger.error(
                "Resultado inválido en finalize | plan=%s | type=%s",
                plan.id,
                type(result).__name__,
            )

            result = ExecutionResult.fail(
                plan_id=plan.id,
                error="ExecutionEngine recibió un resultado inválido.",
                executor=self.name,
                started_at=started_at,
            )

        if result.plan_id != plan.id:
            logger.warning(
                "Corrigiendo plan_id de resultado | result=%s | plan=%s",
                result.plan_id,
                plan.id,
            )

            result.plan_id = plan.id

        if result.is_retry:
            logger.error(
                "Retry llegó a finalize | plan=%s",
                plan.id,
            )

            result = ExecutionResult.fail(
                plan_id=plan.id,
                error=(result.error or "La ejecución terminó en retry inesperadamente."),
                executor=result.executor or self.name,
                retries=result.retries,
                metadata={
                    **dict(result.metadata or {}),
                    "invalid_terminal_retry": True,
                },
                started_at=started_at,
            )

        finished_at = datetime.now(timezone.utc)

        result.set_execution_window(
            started_at=started_at,
            finished_at=finished_at,
        )

        self._apply_plan_state(
            plan,
            result,
        )

        duration = max(
            0.0,
            round(
                time.monotonic() - started_monotonic,
                3,
            ),
        )

        result.metadata.update(
            {
                "engine": self.name,
                "duration": duration,
                "plan_id": plan.id,
                "retries": result.retries,
                "terminal": result.is_terminal,
            }
        )

        self._update_metrics(result)

        self._save_metric(
            plan,
            result,
            duration,
        )

        self._retry_context.pop(
            plan.id,
            None,
        )

        return result

    def _save_metric(
        self,
        plan: ExecutionPlan,
        result: ExecutionResult,
        duration: float,
    ) -> None:
        try:
            metric = ExecutionMetric(
                execution_id=str(uuid.uuid4()),
                plan_id=plan.id,
                intent=plan.intent or "unknown",
                provider=plan.metadata.get(
                    "provider",
                    "unknown",
                ),
                model=plan.metadata.get(
                    "model",
                    "unknown",
                ),
                started_at=(result.started_at or datetime.now(timezone.utc)),
                duration=duration,
                status=result.status,
                retry_count=result.retries,
                error=result.error,
                step_count=len(plan.steps),
                metadata=dict(
                    plan.metadata or {},
                ),
            )

            self.metrics_store.save(
                metric,
            )

        except Exception as exc:
            logger.warning(
                "No se pudo guardar métrica: %s",
                exc,
            )

    # =========================================================
    # Execution context
    # =========================================================

    def _store_step_result(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
        step: ExecutionStep,
        result: ExecutionResult,
    ) -> None:
        if not isinstance(
            result,
            ExecutionResult,
        ):
            raise TypeError(
                "Solo se pueden almacenar ExecutionResult.",
            )

        self.context_manager.record_step_result(
            context,
            step,
            result,
        )

    def _build_step_context(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
        step: ExecutionStep,
    ) -> dict[str, Any]:
        """
        Construye un contexto aislado para el step.

        No modifica directamente el contexto raíz salvo a través
        de record_step_result(), que es responsabilidad del
        ContextManager.
        """

        step_context = dict(context)

        dependencies = self.context_manager.get_dependency_results(
            context,
            step,
        )

        if dependencies:
            execution = dict(
                step_context.get(
                    "execution",
                    {},
                )
                or {}
            )

            execution["dependencies"] = dependencies
            step_context["execution"] = execution

        self._materialize_dependency_outputs(
            step=step,
            dependencies=dependencies,
            step_context=step_context,
        )

        execution = dict(
            step_context.get(
                "execution",
                {},
            )
            or {}
        )

        execution["current_step"] = {
            "id": step.id,
            "description": step.description,
            "unit_type": step.unit_type,
            "unit_name": step.unit_name,
            "params": dict(
                step.params or {},
            ),
        }

        step_context["execution"] = execution

        retry_data = self._retry_context.get(
            plan.id,
        )

        if retry_data:
            step_context["retry_corrections"] = list(
                retry_data.get(
                    "corrections",
                    [],
                )
                or []
            )

            step_context["retry_issues"] = list(
                retry_data.get(
                    "issues",
                    [],
                )
                or []
            )

        logger.info(
            "step_context | keys=%s | arch=%s | summary_len=%s",
            sorted(step_context.keys()),
            bool(step_context.get("architecture")),
            len(
                str(
                    step_context.get(
                        "project_summary",
                    )
                    or ""
                )
            ),
        )

        return step_context

    # =========================================================
    # Path normalization
    # =========================================================

    @staticmethod
    def _normalize_write_path(
        path: str | None,
        fallback: str = "output.txt",
    ) -> str:
        """
        Fuerza path relativo.

        El path nunca debe escapar del target mediante:

            - rutas absolutas
            - ..
            - separadores de Windows
        """

        raw = (path or "").strip() or fallback

        p = Path(raw)

        if p.is_absolute():
            raw = p.name or fallback

        raw = raw.replace(
            "\\",
            "/",
        ).lstrip("/")

        parts = [
            x
            for x in Path(raw).parts
            if x
            not in (
                "",
                ".",
                "..",
            )
        ]

        if not parts:
            parts = [fallback]

        return str(
            Path(*parts),
        )

    # =========================================================
    # Dependency output materialization
    # =========================================================

    def _materialize_dependency_outputs(
        self,
        step: ExecutionStep,
        dependencies: dict[str, Any],
        step_context: dict[str, Any],
    ) -> None:
        """
        Proyecta outputs tipados de dependencias a:

            - step.params  → Skills
            - step_context → Agents

        Los dependencies nuevos pueden ser ExecutionResult.

        Compatibilidad:

            también acepta el formato legacy dict.
        """

        if not dependencies:
            return

        artifacts: list[dict[str, Any]] = []
        evidence_by_type: dict[str, Any] = {}
        plain_texts: list[str] = []

        for dep_id, dep_data in dependencies.items():
            raw: Any = None

            # -------------------------------------------------
            # Nuevo contrato
            # -------------------------------------------------

            if isinstance(
                dep_data,
                ExecutionResult,
            ):
                if not dep_data.is_success:
                    continue

                raw = dep_data.result

            # -------------------------------------------------
            # Legacy
            # -------------------------------------------------

            elif isinstance(
                dep_data,
                dict,
            ):
                status = dep_data.get("status")

                if status is not None and not self._legacy_status_is_success(status):
                    continue

                raw = dep_data.get(
                    "result",
                )

                if isinstance(
                    raw,
                    ExecutionResult,
                ):
                    if not raw.is_success:
                        continue

                    raw = raw.result

                # Envelope:
                #
                # {
                #     "ok": True,
                #     "result": ...
                # }

                if isinstance(raw, dict) and "ok" in raw and "result" in raw:
                    if raw.get("ok") is False:
                        continue

                    raw = raw.get(
                        "result",
                    )

            else:
                continue

            if raw is None:
                continue

            # -------------------------------------------------
            # Plain text
            # -------------------------------------------------

            if isinstance(
                raw,
                str,
            ):
                if raw.strip():
                    plain_texts.append(
                        raw,
                    )

                continue

            if not isinstance(
                raw,
                dict,
            ):
                continue

            payload_type = raw.get(
                "type",
            )

            if payload_type == "code_artifact":
                artifacts.append(
                    raw,
                )

            elif payload_type in {
                "architecture_evidence",
                "quality_evidence",
                "security_evidence",
                "performance_evidence",
                "project_analysis",
            }:
                evidence_by_type[payload_type] = raw

            elif "architecture" in raw and payload_type is None:
                evidence_by_type.setdefault(
                    "architecture_evidence",
                    raw,
                )

            elif payload_type is None and (
                "structure" in raw or "files" in raw or "project" in raw
            ):
                evidence_by_type.setdefault(
                    "project_analysis",
                    raw,
                )

        # -----------------------------------------------------
        # Skills: write_file
        # -----------------------------------------------------

        if step.unit_type == "skill" and step.unit_name == "write_file":
            params = dict(
                step.params or {},
            )

            planned_path = params.get(
                "path",
            )

            needs_path = not params.get(
                "path",
            )

            needs_content = (
                params.get(
                    "content",
                )
                is None
            )

            # -------------------------------------------------
            # code_artifact directo
            # -------------------------------------------------

            if (needs_path or needs_content) and artifacts:
                file_index = 0

                try:
                    file_index = int(
                        params.get(
                            "file_index",
                            0,
                        )
                        or 0
                    )
                except (
                    TypeError,
                    ValueError,
                ):
                    file_index = 0

                files = (
                    artifacts[0].get(
                        "files",
                    )
                    or []
                )

                if 0 <= file_index < len(files):
                    chosen = files[file_index]

                    if not isinstance(
                        chosen,
                        dict,
                    ):
                        chosen = {}

                    if needs_path and chosen.get("path"):
                        params["path"] = chosen["path"]

                    if needs_content and chosen.get("content") is not None:
                        params["content"] = chosen["content"]

            # -------------------------------------------------
            # Texto plano
            # -------------------------------------------------

            needs_path = not params.get(
                "path",
            )

            needs_content = (
                params.get(
                    "content",
                )
                is None
            )

            if needs_content and plain_texts:
                text = plain_texts[0]
                content = text
                path_from_json = None

                stripped = text.strip()

                if "code_artifact" in stripped and "{" in stripped:
                    candidate = stripped

                    if candidate.startswith(
                        "```",
                    ):
                        lines = candidate.split(
                            "\n",
                        )

                        if lines and lines[0].startswith("```"):
                            lines = lines[1:]

                        if lines and lines[-1].strip().startswith("```"):
                            lines = lines[:-1]

                        candidate = "\n".join(
                            lines,
                        ).strip()

                    try:
                        data = json.loads(
                            candidate,
                        )

                    except json.JSONDecodeError:
                        start = candidate.find(
                            "{",
                        )
                        end = candidate.rfind(
                            "}",
                        )

                        data = None

                        if start >= 0 and end > start:
                            try:
                                data = json.loads(
                                    candidate[start : end + 1],
                                )
                            except json.JSONDecodeError:
                                data = None

                    if isinstance(data, dict) and data.get("type") == "code_artifact":
                        files = (
                            data.get(
                                "files",
                            )
                            or []
                        )

                        file_index = 0

                        try:
                            file_index = int(
                                params.get(
                                    "file_index",
                                    0,
                                )
                                or 0
                            )
                        except (
                            TypeError,
                            ValueError,
                        ):
                            file_index = 0

                        if 0 <= file_index < len(files):
                            chosen = files[file_index]

                            if isinstance(
                                chosen,
                                dict,
                            ):
                                if (
                                    chosen.get(
                                        "content",
                                    )
                                    is not None
                                ):
                                    content = chosen["content"]

                                if chosen.get("path"):
                                    path_from_json = chosen["path"]

                params["content"] = content

                if needs_path and not params.get("path"):
                    params["path"] = path_from_json or planned_path or "output.md"

            # -------------------------------------------------
            # Siempre normalizar path
            # -------------------------------------------------

            fallback = planned_path or "output.txt"

            if (
                not isinstance(
                    fallback,
                    str,
                )
                or not fallback.strip()
            ):
                fallback = "output.txt"

            candidate_path = params.get("path") or fallback

            if (
                planned_path
                and Path(
                    str(candidate_path),
                ).is_absolute()
            ):
                candidate_path = planned_path

            params["path"] = self._normalize_write_path(
                (str(candidate_path) if candidate_path else None),
                fallback=str(
                    fallback,
                ),
            )

            step.params = params

            current = dict(
                step_context.get(
                    "execution",
                )
                or {}
            )

            current_step = dict(
                current.get(
                    "current_step",
                )
                or {}
            )

            current_step["params"] = dict(
                params,
            )

            current["current_step"] = current_step
            step_context["execution"] = current

            logger.info(
                "Materializado write_file | path=%s | content_len=%s",
                params.get("path"),
                len(
                    str(
                        params.get(
                            "content",
                            "",
                        )
                    )
                ),
            )

        # -----------------------------------------------------
        # Agents: evidence
        # -----------------------------------------------------

        if step.unit_type == "agent":
            architecture_evidence = evidence_by_type.get(
                "architecture_evidence",
            )

            if isinstance(
                architecture_evidence,
                dict,
            ):
                step_context["architecture"] = architecture_evidence

                if not step_context.get(
                    "project_summary",
                ):
                    step_context["project_summary"] = (
                        architecture_evidence.get(
                            "summary",
                        )
                        or architecture_evidence.get(
                            "project_summary",
                        )
                        or ""
                    )

            project_analysis = evidence_by_type.get(
                "project_analysis",
            )

            if isinstance(
                project_analysis,
                dict,
            ):
                if "architecture" not in step_context:
                    architecture = project_analysis.get(
                        "architecture_context",
                    )

                    if isinstance(
                        architecture,
                        dict,
                    ):
                        step_context["architecture"] = architecture

                summary = (
                    project_analysis.get(
                        "summary",
                    )
                    or project_analysis.get(
                        "project_summary",
                    )
                    or ""
                )

                if summary and not step_context.get(
                    "project_summary",
                ):
                    step_context["project_summary"] = summary

                step_context["project_analysis"] = {
                    "summary": summary,
                    "type": project_analysis.get(
                        "type",
                        "project_analysis",
                    ),
                }

            for key in (
                "quality_evidence",
                "security_evidence",
                "performance_evidence",
            ):
                evidence = evidence_by_type.get(
                    key,
                )

                if isinstance(
                    evidence,
                    dict,
                ):
                    step_context[key] = evidence

            if artifacts:
                step_context["code_artifacts"] = artifacts

            if plain_texts and not (architecture_evidence or project_analysis or artifacts):
                step_context["dependency_text"] = plain_texts[0]

    # =========================================================
    # Retry
    # =========================================================

    def _execute_with_retries(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
        started_at: datetime,
    ) -> ExecutionResult:
        max_retries = max(
            0,
            plan.get_max_retries(),
        )

        retries = 0

        try:
            while True:
                logger.info(
                    "Execution intento | plan=%s | retry=%s/%s",
                    plan.id,
                    retries,
                    max_retries,
                )

                # -------------------------------------------------
                # Execute
                # -------------------------------------------------

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

                if not isinstance(
                    result,
                    ExecutionResult,
                ):
                    raise TypeError(
                        "La ejecución debe devolver ExecutionResult.",
                    )

                # -------------------------------------------------
                # Evaluation
                # -------------------------------------------------

                result = self._evaluate(
                    plan,
                    result,
                    context,
                )

                if not isinstance(
                    result,
                    ExecutionResult,
                ):
                    raise TypeError(
                        "SelfCritic debe devolver ExecutionResult.",
                    )

                result.retries = retries
                result.started_at = started_at

                # -------------------------------------------------
                # Terminal
                # -------------------------------------------------

                if result.is_success:
                    return result

                if result.is_partial:
                    return result

                if result.is_cancelled:
                    return result

                # -------------------------------------------------
                # Estados que pueden provocar retry
                # -------------------------------------------------

                if not (result.is_failure or result.is_retry):
                    logger.error(
                        "Estado inesperado del ExecutionResult | "
                        "plan=%s | status=%s",
                        plan.id,
                        result.status,
                    )

                    return ExecutionResult.fail(
                        plan_id=plan.id,
                        error=(
                            "ExecutionEngine recibió un estado "
                            f"no soportado: {result.status}"
                        ),
                        executor=self.name,
                        retries=retries,
                        metadata={
                            "unexpected_status": result.status,
                        },
                        started_at=started_at,
                    )

                # -------------------------------------------------
                # Agotado
                # -------------------------------------------------

                if retries >= max_retries:
                    error = (
                        result.error
                        or "La ejecución falló y se agotaron los reintentos."
                    )

                    metadata = dict(
                        result.metadata or {},
                    )

                    metadata.update(
                        {
                            "retry_exhausted": True,
                            "retry_count": retries,
                            "max_retries": max_retries,
                        }
                    )

                    logger.error(
                        "Retries agotados | plan=%s | retries=%s/%s",
                        plan.id,
                        retries,
                        max_retries,
                    )

                    return ExecutionResult.fail(
                        plan_id=plan.id,
                        error=error,
                        executor=(result.executor or self.name),
                        retries=retries,
                        metadata=metadata,
                        started_at=started_at,
                    )

                # -------------------------------------------------
                # Preparar siguiente intento
                # -------------------------------------------------

                retries += 1
                self.metrics["retries"] += 1

                retry_data = self._retry_context.get(plan.id) or {}

                result.retries = retries

                result.metadata.update(
                    {
                        "retry_count": retries,
                        "max_retries": max_retries,
                    }
                )

                logger.info(
                    "Preparando retry | plan=%s | retry=%s/%s | "
                    "corrections=%s | issues=%s",
                    plan.id,
                    retries,
                    max_retries,
                    len(
                        retry_data.get(
                            "corrections",
                        )
                        or []
                    ),
                    len(
                        retry_data.get(
                            "issues",
                        )
                        or []
                    ),
                )

                # -------------------------------------------------
                # Reset selectivo
                # -------------------------------------------------

                self._reset_execution_context(
                    plan,
                    context,
                )

                retry_delay = plan.metadata.get(
                    "retry_delay",
                    0.5,
                )

                try:
                    retry_delay = max(
                        0.0,
                        float(retry_delay),
                    )
                except (
                    TypeError,
                    ValueError,
                ):
                    retry_delay = 0.5

                if retry_delay:
                    time.sleep(retry_delay)

        finally:
            self._retry_context.pop(
                plan.id,
                None,
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

        if not isinstance(
            execution,
            dict,
        ):
            execution = {}
            context["execution"] = execution

        completed_steps = execution.get(
            "steps",
        )

        if not isinstance(
            completed_steps,
            dict,
        ):
            completed_steps = {}
            execution["steps"] = completed_steps

        for step in plan.steps:
            previous = completed_steps.get(
                step.id,
            )

            if previous is None:
                step.reset()
                completed_steps.pop(
                    step.id,
                    None,
                )
                continue

            # -------------------------------------------------
            # Nuevo contrato
            # -------------------------------------------------

            if isinstance(
                previous,
                ExecutionResult,
            ):
                if previous.is_success:
                    continue

                step.reset()
                completed_steps.pop(
                    step.id,
                    None,
                )
                continue

            # -------------------------------------------------
            # Legacy
            # -------------------------------------------------

            if isinstance(
                previous,
                dict,
            ):
                if self._dependency_result_is_success(
                    previous,
                ):
                    continue

                step.reset()
                completed_steps.pop(
                    step.id,
                    None,
                )
                continue

            step.reset()
            completed_steps.pop(
                step.id,
                None,
            )

        execution["steps"] = completed_steps

    # =========================================================
    # Single execution
    # =========================================================

    def _execute_single(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
    ) -> ExecutionResult:
        if not plan.execution_unit_type:
            return ExecutionResult.fail(
                plan_id=plan.id,
                error="Plan sin execution_unit_type.",
                executor=self.name,
            )

        if not plan.execution_unit:
            return ExecutionResult.fail(
                plan_id=plan.id,
                error="Plan sin execution_unit.",
                executor=self.name,
            )

        step = ExecutionStep(
            description=(plan.objective or plan.original_task),
            unit_type=plan.execution_unit_type,
            unit_name=plan.execution_unit,
            params=dict(
                plan.params or {},
            ),
        )

        step_context = self._build_step_context(
            plan,
            context,
            step,
        )

        step.mark_running()

        try:
            result = self.dispatcher.dispatch(
                plan,
                step,
                step_context,
            )

            if not isinstance(
                result,
                ExecutionResult,
            ):
                raise TypeError("UnitDispatcher.dispatch " "debe devolver ExecutionResult.")

            step.apply_result(
                result=result.result,
                success=result.is_success,
                error=result.error,
            )

        except Exception as exc:
            step.mark_failed(
                str(exc),
            )

            result = ExecutionResult.fail(
                plan_id=plan.id,
                error=str(exc),
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

        return result

    # =========================================================
    # Scaffold aggregation
    # =========================================================

    def _aggregate_scaffold_results(
        self,
        plan: ExecutionPlan,
        results: list[ExecutionResult],
    ) -> dict[str, Any]:
        modules: list[str] = []
        created: list[str] = []
        adapters: list[str] = []
        errors: list[str] = []

        locale = plan.metadata.get(
            "locale",
        )

        for item in results:
            if item.error:
                errors.append(
                    str(item.error),
                )

            raw = item.result

            if isinstance(raw, dict) and "ok" in raw and "result" in raw:
                if raw.get("ok") is False and raw.get("error"):
                    errors.append(
                        str(
                            raw["error"],
                        )
                    )

                raw = raw.get(
                    "result",
                )

            if not isinstance(
                raw,
                dict,
            ):
                continue

            mod = raw.get(
                "module",
            )

            if mod:
                modules.append(
                    str(mod),
                )

            for path in (
                raw.get(
                    "created",
                )
                or []
            ):
                p = str(path)

                created.append(p)

                if "/adapters/" in p.replace(
                    "\\",
                    "/",
                ):
                    adapters.append(p)

        def uniq(
            seq: list[str],
        ) -> list[str]:
            seen: set[str] = set()
            out: list[str] = []

            for item in seq:
                if item not in seen:
                    seen.add(item)
                    out.append(item)

            return out

        return {
            "type": "module_scaffold_batch",
            "modules": uniq(modules),
            "created": uniq(created),
            "adapters": uniq(adapters),
            "locale": locale,
            "from_spec": plan.metadata.get(
                "from_spec",
            ),
            "steps_ok": sum(1 for result in results if result.is_success),
            "steps_total": len(results),
            "errors": errors,
        }

    def _should_aggregate_scaffold(
        self,
        plan: ExecutionPlan,
        results: list[ExecutionResult],
    ) -> bool:
        if len(results) <= 1:
            return False

        if plan.metadata.get(
            "aggregate_results",
        ):
            return True

        intent = (plan.intent or "").lower()

        if intent in {
            "module_scaffold",
            "ui_scaffold",
        }:
            return True

        names = [f"{step.unit_type}:{step.unit_name}" for step in plan.steps]

        scaffoldish = sum(
            1
            for name in names
            if name
            in {
                "skill:scaffold_module",
                "skill:scaffold_ui_shell",
                "skill:write_file",
            }
        )

        return scaffoldish >= 2

    # =========================================================
    # Analysis → generation → write presentation
    # =========================================================

    def _is_analysis_then_generate_plan(
        self,
        plan: ExecutionPlan,
        executed_steps: list[ExecutionStep],
        results: list[ExecutionResult],
    ) -> bool:
        """
        Detecta planes del tipo:

            task_agent (análisis)
                ↓
            coder (generación)
                ↓
            write_file (persistencia)

        Importante:

            Se utilizan executed_steps + results y no
            plan.steps + results, porque results puede no
            contener todos los steps cuando alguno fue
            reutilizado desde el contexto de ejecución.

        Además se comprueba el orden real de ejecución.
        """

        if len(executed_steps) < 3 or len(results) < 3:
            return False

        units = [
            (
                step.unit_type,
                step.unit_name,
            )
            for step in executed_steps
        ]

        try:
            analysis_index = units.index(
                (
                    "agent",
                    "task_agent",
                ),
            )

            coder_index = units.index(
                (
                    "agent",
                    "coder",
                ),
            )

            write_index = units.index(
                (
                    "skill",
                    "write_file",
                ),
            )

        except ValueError:
            return False

        return analysis_index < coder_index < write_index

    def _build_analysis_and_write_result(
        self,
        plan: ExecutionPlan,
        executed_steps: list[ExecutionStep],
        results: list[ExecutionResult],
        result_payload: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Construye un resultado compuesto pensado para la
        presentación final al usuario:

            1. Análisis producido por task_agent.
            2. Confirmación de write_file.
            3. Ruta absoluta cuando la skill la proporciona.

        La asociación step/result se realiza mediante
        executed_steps + results para evitar desalineaciones
        producidas por steps reutilizados desde contexto.
        """

        analysis_text: str | None = None
        write_result: Any = None
        absolute_path: str | None = None

        # -----------------------------------------------------
        # Asociar correctamente step ↔ result
        # -----------------------------------------------------

        for step, result in zip(
            executed_steps,
            results,
        ):
            if not result.is_success:
                continue

            # -------------------------------------------------
            # task_agent
            # -------------------------------------------------

            if step.unit_type == "agent" and step.unit_name == "task_agent":
                raw = result.result

                if isinstance(
                    raw,
                    str,
                ):
                    if raw.strip():
                        analysis_text = raw.strip()

                elif isinstance(
                    raw,
                    dict,
                ):
                    candidate = raw.get("result") or raw.get("analysis") or raw.get("content")

                    if candidate is not None:
                        analysis_text = str(
                            candidate,
                        ).strip()

                    elif raw:
                        analysis_text = str(
                            raw,
                        )

            # -------------------------------------------------
            # write_file
            # -------------------------------------------------

            elif step.unit_type == "skill" and step.unit_name == "write_file":
                write_result = result.result

                if isinstance(
                    write_result,
                    dict,
                ):
                    absolute_path = write_result.get(
                        "absolute_path",
                    ) or write_result.get(
                        "path",
                    )

        # -----------------------------------------------------
        # Fallback desde result_payload
        # -----------------------------------------------------

        if analysis_text is None:
            for item in result_payload:
                if not (
                    item.get("unit_type") == "agent"
                    and item.get("unit_name") == "task_agent"
                    and item.get("success")
                ):
                    continue

                raw = item.get(
                    "result",
                )

                if isinstance(
                    raw,
                    str,
                ):
                    if raw.strip():
                        analysis_text = raw.strip()

                elif isinstance(
                    raw,
                    dict,
                ):
                    candidate = raw.get("result") or raw.get("analysis") or raw.get("content")

                    if candidate is not None:
                        analysis_text = str(
                            candidate,
                        ).strip()

                    elif raw:
                        analysis_text = str(
                            raw,
                        )

                if analysis_text:
                    break

        # -----------------------------------------------------
        # Fallback para path
        # -----------------------------------------------------

        if absolute_path is None:
            for item in result_payload:
                if not (
                    item.get("unit_type") == "skill"
                    and item.get("unit_name") == "write_file"
                    and item.get("success")
                ):
                    continue

                raw = item.get(
                    "result",
                )

                if isinstance(
                    raw,
                    dict,
                ):
                    absolute_path = raw.get(
                        "absolute_path",
                    ) or raw.get(
                        "path",
                    )

                if absolute_path:
                    break

        # -----------------------------------------------------
        # Resultado final
        # -----------------------------------------------------

        return {
            "type": "analysis_and_write",
            "analysis": (analysis_text or "(No se pudo recuperar el análisis)"),
            "write": {
                "ok": True,
                "path": absolute_path,
                "message": (
                    (
                        "He ejecutado la skill 'write_file' "
                        "correctamente. El archivo se guardó "
                        f"en: {absolute_path}"
                    )
                    if absolute_path
                    else "Archivo escrito correctamente."
                ),
            },
            "summary": (
                "Análisis completado y landing generada correctamente."
                if analysis_text and absolute_path
                else "Proceso completado."
            ),
        }

    # =========================================================
    # Multi-step execution
    # =========================================================

    def _execute_steps(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
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
        executed_steps: list[ExecutionStep] = []
        errors: list[dict[str, str]] = []

        for step in ordered:
            previous = (
                context.get(
                    "execution",
                    {},
                )
                .get(
                    "steps",
                    {},
                )
                .get(
                    step.id,
                )
            )

            # -------------------------------------------------
            # Reutilizar resultado exitoso
            # -------------------------------------------------

            if previous is not None:
                if isinstance(
                    previous,
                    ExecutionResult,
                ):
                    if previous.is_success:
                        logger.info(
                            "Step ya completado; se reutiliza | " "plan=%s | step=%s",
                            plan.id,
                            step.id,
                        )

                        results.append(
                            previous,
                        )

                        executed_steps.append(
                            step,
                        )

                        continue

                elif isinstance(
                    previous,
                    dict,
                ):
                    if self._dependency_result_is_success(
                        previous,
                    ):
                        logger.info(
                            "Step legacy ya completado; se reutiliza | " "plan=%s | step=%s",
                            plan.id,
                            step.id,
                        )

                        # No reconstruimos un ExecutionResult artificial
                        # acá. El ContextManager debería migrar a
                        # ExecutionResult.
                        continue

            # -------------------------------------------------
            # Dependencies
            # -------------------------------------------------

            dependency_failure = self._dependency_failure(
                step,
                context,
            )

            if dependency_failure is not None:
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
                        "skipped": True,
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

                executed_steps.append(
                    step,
                )

                errors.append(
                    {
                        "step": step.description,
                        "unit": step.unit_name,
                        "error": dependency_failure,
                    }
                )

                if plan.should_stop_on_error():
                    break

                continue

            # -------------------------------------------------
            # Step context
            # -------------------------------------------------

            step_context = self._build_step_context(
                plan,
                context,
                step,
            )

            step.mark_running()

            try:
                result = self.dispatcher.dispatch(
                    plan,
                    step,
                    step_context,
                )

                if not isinstance(
                    result,
                    ExecutionResult,
                ):
                    raise TypeError("UnitDispatcher.dispatch " "debe devolver ExecutionResult.")

                step.apply_result(
                    result=result.result,
                    success=result.is_success,
                    error=result.error,
                )

            except Exception as exc:
                step.mark_failed(
                    str(exc),
                )

                result = ExecutionResult.fail(
                    plan_id=plan.id,
                    error=str(exc),
                    executor=self.name,
                    metadata={
                        "step_id": step.id,
                        "step": step.description,
                        "unit": step.unit_name,
                    },
                )

            # -------------------------------------------------
            # Store
            # -------------------------------------------------

            self._store_step_result(
                plan,
                context,
                step,
                result,
            )

            results.append(
                result,
            )

            executed_steps.append(
                step,
            )

            # -------------------------------------------------
            # Retry
            # -------------------------------------------------

            if result.is_retry:
                errors.append(
                    {
                        "step": step.description,
                        "unit": step.unit_name,
                        "error": (result.error or "El step solicitó un reintento."),
                    }
                )

                logger.warning(
                    "Step solicitó retry | plan=%s | step=%s | " "unit=%s | error=%s",
                    plan.id,
                    step.id,
                    step.unit_name,
                    result.error,
                )

                if plan.should_stop_on_error():
                    break

            # -------------------------------------------------
            # Failure
            # -------------------------------------------------

            elif result.is_failure:
                errors.append(
                    {
                        "step": step.description,
                        "unit": step.unit_name,
                        "error": (result.error or "Error desconocido"),
                    }
                )

                if plan.should_stop_on_error():
                    break

            # -------------------------------------------------
            # Cancelled
            # -------------------------------------------------

            elif result.is_cancelled:
                errors.append(
                    {
                        "step": step.description,
                        "unit": step.unit_name,
                        "error": (result.error or "Step cancelado."),
                    }
                )

                if plan.should_stop_on_error():
                    break

        # -----------------------------------------------------
        # Payload por step
        # -----------------------------------------------------

        result_payload = [
            {
                "step_id": step.id,
                "description": step.description,
                "unit_type": step.unit_type,
                "unit_name": step.unit_name,
                "status": result.status,
                "result": result.result,
                "error": result.error,
                "success": result.is_success,
                "partial": result.is_partial,
                "failure": result.is_failure,
                "retry": result.is_retry,
                "cancelled": result.is_cancelled,
                "terminal": result.is_terminal,
            }
            for step, result in zip(
                executed_steps,
                results,
            )
        ]

        # -----------------------------------------------------
        # Retry solicitado
        # -----------------------------------------------------

        retry_requested = any(result.is_retry for result in results)

        if retry_requested:
            detail = "\n".join(
                (f"- {error['step']} " f"({error['unit']}): " f"{error['error']}")
                for error in errors
            )

            return ExecutionResult.retry(
                plan_id=plan.id,
                error=(detail or "Uno o más steps solicitaron " "un reintento."),
                executor=self.name,
                metadata={
                    "steps": result_payload,
                    "step_count": len(results),
                    "retry_requested": True,
                },
            )

        # -----------------------------------------------------
        # Cancelled
        # -----------------------------------------------------

        cancelled = any(result.is_cancelled for result in results)

        if cancelled:
            detail = "\n".join(
                (f"- {error['step']} " f"({error['unit']}): " f"{error['error']}")
                for error in errors
            )

            return ExecutionResult.cancelled(
                plan_id=plan.id,
                error=(detail or "Uno o más steps fueron cancelados."),
                executor=self.name,
                metadata={
                    "steps": result_payload,
                    "step_count": len(results),
                },
            )

        # -----------------------------------------------------
        # Everything successful
        # -----------------------------------------------------

        if not errors:
            # -------------------------------------------------
            # Caso especial:
            #
            # task_agent → coder → write_file
            #
            # La presentación final conserva el análisis y
            # agrega la confirmación de escritura.
            # -------------------------------------------------

            if self._is_analysis_then_generate_plan(
                plan,
                executed_steps,
                results,
            ):
                final_result = self._build_analysis_and_write_result(
                    plan=plan,
                    executed_steps=executed_steps,
                    results=results,
                    result_payload=result_payload,
                )

                return ExecutionResult.success(
                    plan_id=plan.id,
                    result=final_result,
                    executor=self.name,
                    metadata={
                        "steps": result_payload,
                        "step_count": len(results),
                        "presentation": "analysis_then_write",
                    },
                )

            # -------------------------------------------------
            # Scaffold aggregation
            # -------------------------------------------------

            if self._should_aggregate_scaffold(
                plan,
                results,
            ):
                final_result = self._aggregate_scaffold_results(
                    plan,
                    results,
                )
            else:
                final_result = results[-1].result if results else None

            return ExecutionResult.success(
                plan_id=plan.id,
                result=final_result,
                executor=self.name,
                metadata={
                    "steps": result_payload,
                    "step_count": len(results),
                    "aggregated": (
                        isinstance(
                            final_result,
                            dict,
                        )
                        and final_result.get(
                            "type",
                        )
                        == "module_scaffold_batch"
                    ),
                },
            )

        # -----------------------------------------------------
        # Errors
        # -----------------------------------------------------

        detail = "\n".join(
            (f"- {error['step']} " f"({error['unit']}): " f"{error['error']}") for error in errors
        )

        # -----------------------------------------------------
        # Todos fallaron
        # -----------------------------------------------------

        if len(errors) == len(results) and results:
            return ExecutionResult.fail(
                plan_id=plan.id,
                error=detail,
                executor=self.name,
                metadata={
                    "steps": result_payload,
                    "step_count": len(results),
                },
            )

        # -----------------------------------------------------
        # Algunos fallaron
        # -----------------------------------------------------

        return ExecutionResult.partial(
            plan_id=plan.id,
            result=(results[-1].result if results else None),
            error=detail,
            executor=self.name,
            metadata={
                "steps": result_payload,
                "step_count": len(results),
            },
        )

    # =========================================================
    # Dependencies
    # =========================================================

    def _dependency_failure(
        self,
        step: ExecutionStep,
        context: dict[str, Any],
    ) -> str | None:
        if not step.depends_on:
            return None

        execution = context.get(
            "execution",
            {},
        )

        if not isinstance(
            execution,
            dict,
        ):
            return "Contexto de ejecución inválido " "para resolver dependencias."

        completed_steps = execution.get(
            "steps",
            {},
        )

        if not isinstance(
            completed_steps,
            dict,
        ):
            return "Contexto de steps inválido " "para resolver dependencias."

        for dependency_id in step.depends_on:
            dependency = completed_steps.get(
                dependency_id,
            )

            if dependency is None:
                return "Dependencia no ejecutada: " f"{dependency_id}"

            # -------------------------------------------------
            # Nuevo contrato
            # -------------------------------------------------

            if isinstance(
                dependency,
                ExecutionResult,
            ):
                if dependency.is_success:
                    continue

                if dependency.error:
                    return (
                        f"Dependencia fallida: "
                        f"{dependency_id} "
                        f"(status={dependency.status}): "
                        f"{dependency.error}"
                    )

                return (
                    f"Dependencia no válida: " f"{dependency_id} " f"(status={dependency.status})"
                )

            # -------------------------------------------------
            # Legacy
            # -------------------------------------------------

            if isinstance(
                dependency,
                dict,
            ):
                if self._dependency_result_is_success(
                    dependency,
                ):
                    continue

                error = dependency.get(
                    "error",
                )

                if error:
                    return (
                        f"Dependencia fallida: "
                        f"{dependency_id} "
                        f"(status={dependency.get('status')}): "
                        f"{error}"
                    )

                return (
                    f"Dependencia no válida: "
                    f"{dependency_id} "
                    f"(status={dependency.get('status')})"
                )

            return f"Dependencia inválida: " f"{dependency_id}"

        return None

    # =========================================================
    # Evaluation
    # =========================================================

    def _evaluate(
        self,
        plan: ExecutionPlan,
        result: ExecutionResult,
        context: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        """
        Evalúa únicamente resultados que pueden ser evaluados.

        success / partial
            → SelfCritic

        failure / cancelled
            → se mantienen

        retry
            → se mantiene
        """

        if not (result.is_success or result.is_partial):
            return result

        if not plan.metadata.get("requires_self_critic", False):
            return result

        evaluation = self.critic.evaluate(
            plan=plan,
            result=result,
            context=context or {},
        )

        result.metadata["evaluation"] = evaluation

        try:
            self.engram.save(
                (
                    f"SelfCritic: {plan.id} - "
                    f"score={evaluation.get('score')}"
                ),
                tags=[
                    "self_critic",
                    f"plan_{plan.id}",
                    f"score_{evaluation.get('score', 0)}",
                ],
            )
        except Exception:
            logger.debug(
                "No se pudo persistir SelfCritic "
                "en EngramMemory.",
                exc_info=True,
            )

        if evaluation.get(
            "pass",
            True,
        ):
            return result

        corrections = evaluation.get(
            "corrections",
            [],
        )

        issues = evaluation.get(
            "issues",
            [],
        )

        self._retry_context[plan.id] = {
            "corrections": corrections,
            "issues": issues,
        }

        return ExecutionResult.retry(
            plan_id=plan.id,
            error=(
                evaluation.get(
                    "reason",
                    "Evaluación fallida",
                )
            ),
            retries=result.retries,
            executor="self_critic",
            metadata={
                **dict(
                    result.metadata or {},
                ),
                "evaluation": evaluation,
                "corrections": corrections,
                "issues": issues,
            },
            started_at=result.started_at,
        )

    # =========================================================
    # Learning
    # =========================================================

    def _learn(
        self,
        plan: ExecutionPlan,
        result: ExecutionResult,
    ) -> None:
        if not (result.is_success or result.is_partial):
            return

        try:
            proposed = self.learner.extract_and_learn(
                user_query=plan.original_task,
                assistant_response=str(
                    result.result or result.error or "",
                ),
            )

            if proposed:
                logger.info(
                    "Learning candidate creado | " "plan=%s | task=%s",
                    plan.id,
                    (plan.original_task or "")[:80],
                )

        except Exception as exc:
            logger.warning(
                "Learning post-ejecución falló: %s",
                exc,
            )

    # =========================================================
    # Ordering
    # =========================================================

    def _resolve_order(
        self,
        steps: list[ExecutionStep],
    ) -> list[ExecutionStep]:
        ids = [step.id for step in steps]

        seen: set[str] = set()
        duplicates: set[str] = set()

        for step in steps:
            if step.id in seen:
                duplicates.add(
                    step.id,
                )

            seen.add(
                step.id,
            )

        if duplicates:
            raise ValueError("IDs de steps duplicados: " f"{sorted(duplicates)}")

        ordered: list[ExecutionStep] = []
        resolved: set[str] = set()

        pending = list(steps)
        available_ids = set(ids)

        while pending:
            progress = False

            for step in pending[:]:
                missing = [
                    dependency for dependency in step.depends_on if dependency not in available_ids
                ]

                if missing:
                    raise ValueError("Dependencias inexistentes: " f"{missing}")

                if all(dependency in resolved for dependency in step.depends_on):
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
                raise RuntimeError("Dependencias circulares " "en el plan.")

        return ordered

    # =========================================================
    # State
    # =========================================================

    def _apply_plan_state(
        self,
        plan: ExecutionPlan,
        result: ExecutionResult,
    ) -> None:
        if result.is_success:
            plan.mark_completed()
            return

        if result.is_partial:
            plan.mark_partial()
            return

        if result.is_failure:
            plan.mark_failed()
            return

        if result.is_cancelled:
            plan.mark_cancelled()
            return

        if result.is_retry:
            logger.error(
                "Intento de finalizar plan en retry | " "plan=%s",
                plan.id,
            )

    # =========================================================
    # Metrics
    # =========================================================

    def _update_metrics(
        self,
        result: ExecutionResult,
    ) -> None:
        if result.is_success:
            self.metrics["success"] += 1
            return

        if result.is_partial:
            self.metrics["partial"] += 1
            return

        if result.is_failure:
            self.metrics["failed"] += 1
            return

        if result.is_cancelled:
            self.metrics["cancelled"] += 1
            return

        if result.is_retry:
            logger.warning("ExecutionResult retry llegó a métricas " "sin ser terminal.")

    def get_metrics(self) -> dict[str, int]:
        return dict(
            self.metrics,
        )

    # =========================================================
    # Failure helper
    # =========================================================

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

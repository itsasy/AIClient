from __future__ import annotations

import json
import logging
from typing import Any

from core.execution_plan import ExecutionPlan
from llm.prompt_type import PromptType

logger = logging.getLogger(__name__)

class PromptCompositionMixin:
    def _compose(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
        prompt_type: PromptType,
        *,
        lean: bool,
    ) -> str:
        sections: list[str] = [self.SYSTEM_INSTRUCTIONS]

        if prompt_type is PromptType.CRITIQUE:
            sections.append(self.CRITIQUE_INSTRUCTIONS)

        agent_role = context.get("agent_role")
        if agent_role:
            sections.append(self._section("Rol de ejecución", str(agent_role)))

        # Tarea: preferir coding_task si existe (enrich / coder)
        coding_task = context.get("coding_task")
        if coding_task:
            sections.append(self._section("Tarea de generación", str(coding_task)))
        else:
            sections.append(self._section("Tarea del usuario", plan.original_task or ""))

        sections.append(
            self._section(
                "ExecutionPlan",
                self._build_plan_section(plan, lean=lean),
            )
        )

        analysis_requirements = context.get("analysis_requirements")
        if analysis_requirements:
            sections.append(
                self._section(
                    "Requisitos de análisis",
                    self._serialize(analysis_requirements),
                )
            )

        requested_output = context.get("requested_output")
        if requested_output:
            sections.append(
                self._section(
                    "Formato de salida solicitado",
                    self._serialize(requested_output),
                )
            )

        requested_paths = context.get("requested_paths")
        if requested_paths:
            sections.append(
                self._section(
                    "Paths solicitados",
                    self._serialize(requested_paths),
                )
            )

        # Standards explícitos (consistencia full-stack)
        standards = context.get("standards")
        if standards:
            sections.append(
                self._section(
                    "Standards del proyecto (obligatorio respetar)",
                    self._serialize(standards),
                )
            )

        locale_summary = context.get("locale_summary") or context.get("locale")
        if locale_summary:
            sections.append(
                self._section(
                    "Locale / región",
                    self._serialize(locale_summary),
                )
            )

        project_summary = context.get("project_summary")
        if project_summary:
            sections.append(self._section("Resumen del proyecto", str(project_summary)))

        architecture = context.get("architecture")
        if architecture:
            sections.append(
                self._section(
                    "Arquitectura (estructura, sin contenidos de archivo)",
                    self._serialize(architecture),
                )
            )

        dependency_text = context.get("dependency_text")
        if dependency_text:
            sections.append(
                self._section(
                    "Salida de dependencia previa",
                    str(dependency_text),
                )
            )

        # Resto de evidencia (sin specialized)
        skip = set(self.SPECIALIZED_CONTEXT_KEYS) | {
            "standards",
            "locale",
            "locale_summary",
            "project_summary",
            "architecture",
            "dependency_text",
            "coding_task",
            "project_analysis",
        }
        general = {key: value for key, value in context.items() if key not in skip}
        if general:
            sections.append(
                self._section(
                    "Contexto y evidencia disponible",
                    self._serialize(general),
                )
            )

        retry_issues = context.get("retry_issues")
        retry_corrections = context.get("retry_corrections")
        if retry_issues or retry_corrections:
            sections.append(
                self._section(
                    "Correcciones de una ejecución anterior",
                    self._serialize(
                        {
                            "issues": retry_issues or [],
                            "corrections": retry_corrections or [],
                        }
                    ),
                )
            )

        execution = context.get("execution")
        if execution:
            sections.append(
                self._section(
                    "Evidencia de ejecución",
                    self._serialize(execution),
                )
            )

        additional = context.get("additional_instructions")
        if additional:
            sections.append(self._section("Instrucciones adicionales", str(additional)))

        if prompt_type is PromptType.CRITIQUE:
            sections.append(
                self._section(
                    "Instrucciones finales",
                    """
Evalúa exclusivamente el resultado disponible.

No ejecutes nuevamente la tarea.
No propongas cambios basados en información inexistente.
No confundas una limitación de evidencia con un error de ejecución.

Devuelve únicamente el JSON definido en "Modo de evaluación".
""".strip(),
                )
            )
        else:
            final = """
Realiza la tarea utilizando únicamente la información disponible.

Cuando debas analizar una implementación:
1. identifica primero los hechos observables;
2. separa las inferencias de los hechos;
3. indica explícitamente qué información no puede determinarse;
4. evita completar huecos con suposiciones;
5. respeta las restricciones del ExecutionPlan y los Standards;
6. si existe información de retry, corrige específicamente los problemas
   señalados sin introducir cambios no justificados.

Cuando generes código o HTML:
1. respeta formato de salida (code_artifact / paths) si se indicó;
2. no inventes stack ni design system nuevo;
3. no copies marcas ni claims de sitios de referencia;
4. operaciones de pago: contratos + idempotency_key si aplica.

La respuesta debe ser concreta, técnica y específica para el proyecto.
""".strip()
            sections.append(self._section("Instrucciones finales", final))

        return "\n\n".join(section.strip() for section in sections if section and section.strip())

    def _build_plan_section(
        self,
        plan: ExecutionPlan,
        *,
        lean: bool,
    ) -> str:
        if lean:
            plan_data: dict[str, Any] = {
                "plan_id": plan.id,
                "intent": plan.intent,
                "intent_category": plan.intent_category,
                "objective": plan.objective,
            }
            # Solo metadata útil
            meta = getattr(plan, "metadata", None) or {}
            slim_meta = {
                k: meta[k] for k in ("locale", "workflow", "enrich", "lean_prompt") if k in meta
            }
            if slim_meta:
                plan_data["metadata"] = slim_meta
            return self._serialize(plan_data)

        plan_data = {
            "plan_id": plan.id,
            "original_task": plan.original_task,
            "intent": plan.intent,
            "intent_category": plan.intent_category,
            "objective": plan.objective,
            "execution_unit_type": plan.execution_unit_type,
            "execution_unit": plan.execution_unit,
            "execution_policy": plan.execution_policy,
            "metadata": {
                k: v
                for k, v in (plan.metadata or {}).items()
                if k
                not in {
                    "loaded_context",
                    "execution_context",
                }
            },
        }
        if plan.steps:
            plan_data["steps"] = [
                {
                    "id": step.id,
                    "description": step.description,
                    "unit_type": step.unit_type,
                    "unit_name": step.unit_name,
                    "depends_on": list(step.depends_on),
                    "params": {
                        k: v
                        for k, v in dict(step.params or {}).items()
                        if k not in {"content"}  # no volcar content enorme
                    },
                }
                for step in plan.steps
            ]
        return self._serialize(plan_data)

    @staticmethod
    def _section(title: str, content: str) -> str:
        return f"""
## {title}

{content}
""".strip()

    @staticmethod
    def _serialize(value: Any) -> str:
        if isinstance(value, str):
            return value
        try:
            return json.dumps(
                value,
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        except Exception:
            logger.exception("Error serializando contexto.")
            return str(value)

    def _truncate_prompt(self, prompt: str) -> str:
        limit = self.max_context_chars
        if len(prompt) <= limit:
            return prompt

        notice = (
            "\n\n[SYSTEM NOTICE]\n"
            "El contexto fue reducido por límite de tamaño. "
            "No inferir información ausente."
        )

        # Preferir recortar evidencia general y architecture
        for marker in (
            "## Contexto y evidencia disponible",
            "## Arquitectura (estructura, sin contenidos de archivo)",
            "## Evidencia de ejecución",
        ):
            context_index = prompt.find(marker)
            if context_index == -1:
                continue

            before = prompt[:context_index]
            final_marker = "\n## Instrucciones finales"
            final_index = prompt.find(final_marker, context_index)
            after = prompt[final_index:] if final_index != -1 else ""

            available = limit - len(before) - len(after) - len(notice)
            if available <= 200:
                continue

            rest = prompt[context_index + len(marker) :]
            if final_index != -1:
                rest = prompt[context_index + len(marker) : final_index]

            if len(rest) > available:
                rest = rest[:available] + "\n[CONTEXTO REDUCIDO]"

            result = before + marker + "\n\n" + rest.strip() + after + notice
            if len(result) <= limit:
                return result
            return result[:limit]

        return prompt[: max(0, limit - len(notice))] + notice

    @staticmethod
    def _is_lean(plan: ExecutionPlan, context: dict[str, Any]) -> bool:
        if context.get("lean_prompt") in (True, "true", "1", 1):
            return True
        meta = getattr(plan, "metadata", None) or {}
        if meta.get("lean_prompt") is True:
            return True
        # Generación de código / landings / enrich: preferir lean
        intent = (getattr(plan, "intent", None) or "").lower()
        category = (getattr(plan, "intent_category", None) or "").lower()
        if intent in {
            "file_creation",
            "code_generation",
            "ui_scaffold",
            "module_scaffold",
        }:
            return True
        if category in {"code", "file"}:
            return True
        if context.get("coding_task"):
            return True
        return False


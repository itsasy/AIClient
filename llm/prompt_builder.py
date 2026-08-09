from __future__ import annotations

import json
import logging
from typing import Any

from core.execution_plan import ExecutionPlan

logger = logging.getLogger(__name__)


class PromptBuilder:
    """
    Construye prompts deterministas para proveedores LLM.

    Responsabilidades:
        - Convertir ExecutionPlan + contexto en un prompt.
        - Normalizar y limitar el contexto.
        - Separar instrucciones, tarea, plan y evidencia.
        - Preservar la distinción entre hechos e inferencias.

    No:
        - Selecciona proveedores.
        - Ejecuta herramientas.
        - Decide planificación.
        - Ejecuta agentes o skills.
        - Modifica el ExecutionPlan.
    """

    MAX_CONTEXT_CHARS = 30_000

    SYSTEM_INSTRUCTIONS = """
Eres un ingeniero de software senior y arquitecto de sistemas.

Tu respuesta debe basarse únicamente en la evidencia proporcionada
por la tarea, el ExecutionPlan y el contexto disponible.

Reglas obligatorias:

1. No inventes componentes, archivos, tecnologías, servicios ni capacidades.
2. No afirmes como hecho aquello que solo puede inferirse.
3. Diferencia explícitamente entre:
   - hechos observados;
   - inferencias razonables;
   - información desconocida.
4. No confundas una estructura de carpetas con un límite arquitectónico.
5. No describas un sistema como microservicios sin evidencia explícita.
6. No inventes infraestructura, bases de datos, colas, APIs o comunicaciones
   que no estén presentes en la evidencia.
7. Si la información disponible es insuficiente, indícalo claramente.
8. Prioriza la implementación y evidencia real sobre descripciones genéricas.
9. Respeta las restricciones y requisitos incluidos en el contexto.
10. Responde en español salvo que la tarea solicite explícitamente otro idioma.
""".strip()

    CONTEXT_PRIORITY = (
        "agent_role",
        "analysis_requirements",
        "requested_output",
        "project_summary",
        "architecture",
        "project_analysis",
        "standards",
        "gentleman",
        "swarmforge",
        "engram",
        "retry_issues",
        "retry_corrections",
        "execution",
        "additional_instructions",
    )

    def __init__(
        self,
        max_context_chars: int | None = None,
    ) -> None:
        self.max_context_chars = (
            max_context_chars if max_context_chars is not None else self.MAX_CONTEXT_CHARS
        )

        if self.max_context_chars <= 0:
            raise ValueError("max_context_chars debe ser mayor que cero.")

    # ==========================================================
    # Public API
    # ==========================================================

    def build(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any] | None = None,
    ) -> str:
        """
        Construye el prompt final para el proveedor LLM.
        """

        if plan is None:
            raise ValueError("plan no puede ser None.")

        raw_context = dict(context or {})

        logger.info(
            "Construyendo prompt | plan=%s | context=%s",
            plan.id,
            list(raw_context.keys()),
        )

        prepared_context = self._prepare_context(
            raw_context,
        )

        prompt = self._compose(
            plan=plan,
            context=prepared_context,
        )

        if len(prompt) > self.max_context_chars:
            logger.warning(
                "Prompt excede límite | chars=%s | max=%s",
                len(prompt),
                self.max_context_chars,
            )

            prompt = self._truncate_prompt(
                prompt,
            )

        logger.info(
            "Prompt construido | plan=%s | chars=%s",
            plan.id,
            len(prompt),
        )

        return prompt

    # ==========================================================
    # Context preparation
    # ==========================================================

    def _prepare_context(
        self,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Selecciona y normaliza únicamente las partes de contexto
        que tienen significado para el LLM.
        """

        prepared: dict[str, Any] = {}

        for key in self.CONTEXT_PRIORITY:

            if key not in context:
                continue

            value = context[key]

            if value is None:
                continue

            if key == "architecture":
                value = self._sanitize_architecture(
                    value,
                )

            elif key == "execution":
                value = self._sanitize_execution(
                    value,
                )

            elif key in {
                "retry_issues",
                "retry_corrections",
            }:
                value = self._sanitize_list(
                    value,
                )

            prepared[key] = value

        return prepared

    # ==========================================================
    # Architecture sanitization
    # ==========================================================

    def _sanitize_architecture(
        self,
        architecture: Any,
    ) -> Any:
        """
        Reduce información innecesaria del análisis arquitectónico.

        Especialmente evita introducir contenido fuente completo
        cuando el contexto ya contiene metadatos suficientes.
        """

        if not isinstance(
            architecture,
            dict,
        ):
            return architecture

        result = dict(
            architecture,
        )

        files = result.get(
            "files",
        )

        if isinstance(
            files,
            list,
        ):
            clean_files = []

            for file_data in files:

                if not isinstance(
                    file_data,
                    dict,
                ):
                    continue

                clean_file = {
                    key: file_data.get(key)
                    for key in (
                        "path",
                        "filename",
                        "extension",
                        "language",
                        "lines",
                        "size",
                    )
                    if key in file_data
                }

                clean_files.append(
                    clean_file,
                )

            result["files"] = clean_files

        # El contenido fuente completo no pertenece
        # automáticamente al resumen arquitectónico.
        result.pop(
            "content",
            None,
        )

        return result

    # ==========================================================
    # Execution sanitization
    # ==========================================================

    @staticmethod
    def _sanitize_execution(
        execution: Any,
    ) -> Any:
        """
        Expone únicamente información relevante de la ejecución actual.
        """

        if not isinstance(
            execution,
            dict,
        ):
            return execution

        allowed_keys = {
            "plan_id",
            "task",
            "current_step",
            "dependencies",
            "steps",
        }

        return {key: execution.get(key) for key in allowed_keys if key in execution}

    # ==========================================================
    # Generic sanitization
    # ==========================================================

    @staticmethod
    def _sanitize_list(
        value: Any,
    ) -> list[str]:
        """
        Normaliza listas de issues/corrections.
        """

        if value is None:
            return []

        if isinstance(
            value,
            str,
        ):
            return [value]

        if not isinstance(
            value,
            (list, tuple, set),
        ):
            return [str(value)]

        return [str(item) for item in value if item is not None]

    # ==========================================================
    # Serialization
    # ==========================================================

    @staticmethod
    def _serialize(
        value: Any,
    ) -> str:
        """
        Serializa contexto de forma estable.
        """

        try:
            return json.dumps(
                value,
                ensure_ascii=False,
                indent=2,
                default=str,
            )

        except Exception:
            logger.exception(
                "Error serializando contexto.",
            )

            return str(
                value,
            )

    # ==========================================================
    # Plan representation
    # ==========================================================

    def _build_plan_section(
        self,
        plan: ExecutionPlan,
    ) -> str:
        """
        Convierte el ExecutionPlan en una representación
        explícita y controlada para el LLM.
        """

        plan_data = {
            "plan_id": plan.id,
            "original_task": plan.original_task,
            "intent": plan.intent,
            "intent_category": plan.intent_category,
            "objective": plan.objective,
            "execution_unit_type": plan.execution_unit_type,
            "execution_unit": plan.execution_unit,
            "execution_policy": plan.execution_policy,
            "metadata": plan.metadata,
        }

        if plan.steps:
            plan_data["steps"] = [
                {
                    "id": step.id,
                    "description": step.description,
                    "unit_type": step.unit_type,
                    "unit_name": step.unit_name,
                    "depends_on": list(
                        step.depends_on,
                    ),
                    "params": dict(
                        step.params,
                    ),
                }
                for step in plan.steps
            ]

        return self._serialize(
            plan_data,
        )

    # ==========================================================
    # Prompt composition
    # ==========================================================

    def _compose(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
    ) -> str:
        """
        Compone el prompt final en secciones previsibles.
        """

        sections: list[str] = [
            self.SYSTEM_INSTRUCTIONS,
        ]

        # ------------------------------------------------------
        # Agent role
        # ------------------------------------------------------

        agent_role = context.get(
            "agent_role",
        )

        if agent_role:
            sections.append(
                self._section(
                    "Rol de ejecución",
                    str(agent_role),
                )
            )

        # ------------------------------------------------------
        # Task
        # ------------------------------------------------------

        sections.append(
            self._section(
                "Tarea del usuario",
                plan.original_task,
            )
        )

        # ------------------------------------------------------
        # Plan
        # ------------------------------------------------------

        sections.append(
            self._section(
                "ExecutionPlan",
                self._build_plan_section(
                    plan,
                ),
            )
        )

        # ------------------------------------------------------
        # Requirements
        # ------------------------------------------------------

        analysis_requirements = context.get(
            "analysis_requirements",
        )

        if analysis_requirements:
            sections.append(
                self._section(
                    "Requisitos de análisis",
                    self._serialize(
                        analysis_requirements,
                    ),
                )
            )

        requested_output = context.get(
            "requested_output",
        )

        if requested_output:
            sections.append(
                self._section(
                    "Formato de salida solicitado",
                    self._serialize(
                        requested_output,
                    ),
                )
            )

        # ------------------------------------------------------
        # Evidence / context
        # ------------------------------------------------------

        if context:
            sections.append(
                self._section(
                    "Contexto y evidencia disponible",
                    self._serialize(
                        context,
                    ),
                )
            )

        # ------------------------------------------------------
        # Retry information
        # ------------------------------------------------------

        retry_issues = context.get(
            "retry_issues",
        )

        retry_corrections = context.get(
            "retry_corrections",
        )

        if retry_issues or retry_corrections:

            retry_payload = {
                "issues": retry_issues or [],
                "corrections": retry_corrections or [],
            }

            sections.append(
                self._section(
                    "Correcciones de una ejecución anterior",
                    self._serialize(
                        retry_payload,
                    ),
                )
            )

        # ------------------------------------------------------
        # Final instructions
        # ------------------------------------------------------

        sections.append("""
## Instrucciones finales

Realiza la tarea utilizando únicamente la información disponible.

Cuando debas analizar una implementación:

1. identifica primero los hechos observables;
2. separa las inferencias de los hechos;
3. indica explícitamente qué información no puede determinarse;
4. evita completar huecos con suposiciones;
5. respeta las restricciones del ExecutionPlan;
6. si existe información de retry, corrige específicamente los problemas
   señalados sin introducir cambios no justificados.

La respuesta debe ser concreta, técnica y específica para el proyecto.
""".strip())

        return "\n\n".join(section.strip() for section in sections if section and section.strip())

    # ==========================================================
    # Section helper
    # ==========================================================

    @staticmethod
    def _section(
        title: str,
        content: str,
    ) -> str:
        return f"""
## {title}

{content}
""".strip()

    # ==========================================================
    # Truncation
    # ==========================================================

    def _truncate_prompt(
        self,
        prompt: str,
    ) -> str:
        """
        Reduce el prompt sin dejar un JSON parcialmente truncado.

        La estrategia elimina primero el bloque de contexto/evidencia,
        preservando instrucciones y ExecutionPlan.
        """

        limit = self.max_context_chars

        if len(prompt) <= limit:
            return prompt

        notice = (
            "\n\n[SYSTEM NOTICE]\n"
            "El contexto fue reducido por límite de tamaño. "
            "No inferir información ausente."
        )

        # Buscar la sección de contexto.
        marker = "## Contexto y evidencia disponible"

        context_index = prompt.find(
            marker,
        )

        if context_index != -1:

            before = prompt[:context_index]

            # Conservar las instrucciones finales si existen.
            final_marker = "\n## Instrucciones finales"

            final_index = prompt.find(
                final_marker,
                context_index,
            )

            after = prompt[final_index:] if final_index != -1 else ""

            available = limit - len(before) - len(after) - len(notice)

            if available > 0:

                context_content = prompt[context_index + len(marker) :]

                context_content = context_content.strip()

                if len(context_content) > available:
                    context_content = context_content[:available] + "\n[CONTEXTO REDUCIDO]"

                result = before + marker + "\n\n" + context_content + after + notice

                return result[:limit]

        # Fallback seguro.
        return prompt[: max(0, limit - len(notice))] + notice

    # ==========================================================
    # Inspection
    # ==========================================================

    def get_max_context_chars(self) -> int:
        return self.max_context_chars

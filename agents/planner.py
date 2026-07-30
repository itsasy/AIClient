import json
import logging
from typing import Optional

from agents.base import Agent
from core.spec_manager import SpecManager
from core.engram_memory import EngramMemory
from llm.provider_manager import ProviderManager
from llm.provider_selector import ProviderSelector
from skills.manager import SkillManager
from agents.self_critic import SelfCriticAgent

logger = logging.getLogger(__name__)


class PlannerAgent(Agent):
    name = "planner"
    role = "Planificador y Ejecutor Autónomo con SDD"

    def __init__(self):
        self.skill_manager = SkillManager()
        self.provider_manager = ProviderManager()
        self.spec_manager = SpecManager()
        self.engram = EngramMemory()
        self.critic = SelfCriticAgent()

    def process(
        self,
        task: str,
        context: dict = None,
        skill_name: str = None,
        skill_params: dict = None,
    ) -> str:
        import re

        is_create_intent = bool(
            re.search(r"\b(crea|crear|genera|generar|nueva|nuevo|haz|hazme)\b", task, re.IGNORECASE)
            and re.search(r"\b(spec|especificación|plan)\b", task, re.IGNORECASE)
        )

        spec_name = self._extract_spec_name(task)

        if is_create_intent:
            logger.info("Intención de crear nueva Spec detectada.")
            spec = self._generate_spec_from_task(task, context)
            if not spec:
                return "❌ No se pudo generar una especificación válida para la tarea."

            if spec_name:
                spec["name"] = spec_name

            self.spec_manager.save_spec(
                name=spec["name"],
                description=spec["description"],
                objective=spec["objective"],
                criteria=spec["criteria"],
                constraints=spec.get("constraints", []),
                steps=spec.get("steps", []),
            )

            return (
                f"✅ **Spec '{spec['name']}'** creada correctamente.\n\n"
                f"**Objetivo:** {spec.get('objective', '')}\n\n"
                f"**Descripción:** {spec.get('description', '')}\n\n"
                f"Usa: `ai \"ejecuta spec {spec['name']}\"` para ejecutarla."
            )

        if spec_name:
            spec = self.spec_manager.load_spec_by_name(spec_name)
            if spec:
                logger.info("Cargando Spec existente: %s", spec_name)
                return self._execute_spec(spec, context)
            return f"⚠️ No se encontró la especificación '{spec_name}'. ¿Quieres crearla?"

        logger.info("Generando nueva Spec a partir de la tarea: %s", task[:100])
        spec = self._generate_spec_from_task(task, context)
        if not spec:
            return "❌ No se pudo generar una especificación válida para la tarea."

        self.spec_manager.save_spec(
            name=spec["name"],
            description=spec["description"],
            objective=spec["objective"],
            criteria=spec["criteria"],
            constraints=spec.get("constraints", []),
            steps=spec.get("steps", []),
        )
        return self._execute_spec(spec, context)

    def _extract_spec_name(self, task: str) -> Optional[str]:
        """Extrae el nombre de una spec de la tarea de forma más robusta."""
        import re

        match = re.search(
            r"(?:llamado|nombre)\s+[\"']?([a-zA-Z0-9_-]+)[\"']?",
            task,
            re.IGNORECASE,
        )
        if match:
            return match.group(1)

        match = re.search(
            r"(?:spec|especificación|plan)\s+[\"']?([a-zA-Z0-9_-]+)[\"']?",
            task,
            re.IGNORECASE,
        )
        if match:
            name = match.group(1)
            if name.lower() not in {"para", "un", "una", "de", "el", "la", "los", "las"}:
                return name

        # 3. Fallback: última palabra alfanumérica
        words = task.split()
        if words:
            last = words[-1].strip(".,;:!?\"'")
            if re.match(r"^[a-zA-Z0-9_-]+$", last):
                return last

        return None

    def _generate_spec_from_task(self, task: str, context: dict) -> dict:
        """Usa el LLM para generar una Spec estructurada a partir de la tarea."""
        provider, fallback_chain = ProviderSelector.select(task=task, skill_name="plan")
        prompt = f"""
Eres un arquitecto de software. A partir de la siguiente tarea del usuario, genera una especificación estructurada (Spec) en formato JSON.

Tarea: {task}

Contexto adicional: {context or "No hay contexto adicional."}

La Spec debe tener estos campos:
- name: nombre corto (sin espacios)
- description: descripción detallada
- objective: objetivo principal
- criteria: lista de criterios de éxito (mínimo 3)
- constraints: lista de restricciones (opcional, mínimo 1)
- steps: lista de pasos sugeridos (cada paso con: description, skill, params)

Devuelve SOLO el JSON, sin texto adicional.
Ejemplo:
{{
  "name": "mi_proyecto",
  "description": "Crear un módulo de autenticación",
  "objective": "Implementar registro, login y logout",
  "criteria": ["Los usuarios pueden registrarse", "Los usuarios pueden iniciar sesión", "Los usuarios pueden cerrar sesión"],
  "constraints": ["Usar JWT", "No usar librerías externas"],
  "steps": [
    {{"description": "Crear modelo User", "skill": "code", "params": {{"task": "Genera modelo User con campos email y password", "language": "python"}}}},
    {{"description": "Crear endpoint de registro", "skill": "code", "params": {{"task": "Crea endpoint /register", "language": "python"}}}}
  ]
}}
"""
        try:
            response = self.provider_manager.generate(
                prompt, provider_name=provider, fallback_chain=fallback_chain
            )
            # Extraer JSON
            start = response.find("{")
            end = response.rfind("}") + 1
            if start != -1 and end != -1:
                spec = json.loads(response[start:end])
                return spec
            else:
                raise ValueError("No se encontró JSON en la respuesta")
        except Exception as e:
            logger.exception("Error generando spec: %s", e)
            return None

    def _execute_spec(self, spec: dict, context: dict) -> str:
        """
        Ejecuta una spec: genera un plan detallado y lo ejecuta paso a paso
        utilizando subagentes con auto-corrección.
        """
        # 1. Actualizar estado a "executing"
        self.spec_manager.update_status(spec["name"], "executing")

        # 2. Generar un plan detallado a partir de la spec
        plan = self._generate_plan_from_spec(spec, context)
        if not plan:
            self.spec_manager.update_status(spec["name"], "failed")
            return f"❌ No se pudo generar un plan para la spec '{spec['name']}'."

        # 3. Inicializar subagente
        from core.subagent import Subagent

        subagent = Subagent()

        # 4. Ejecutar cada paso del plan con validación y reintentos
        results = []
        for i, step in enumerate(plan, 1):
            desc = step.get("description", f"Paso {i}")
            skill = step.get("skill")
            params = step.get("params", {})

            logger.info("Ejecutando paso %d: %s (%s)", i, desc, skill)

            # Ejecutar con subagente (retry + auto-corrección)
            try:
                skill_result, eval_result = subagent.execute_with_retry(
                    step_description=desc,
                    skill_name=skill,
                    params=params,
                    context=context,
                    max_retries=2,
                )

                # Extraer salida legible
                output = subagent._extract_output(skill_result)
                alignment = eval_result.get("alignment_score", 0) if eval_result else 0

                if alignment >= 5:
                    results.append(f"✅ **Paso {i} - {desc}** (Score: {alignment})\n{output[:500]}")
                else:
                    results.append(
                        f"⚠️ **Paso {i} - {desc}** (Score: {alignment} - Bajo)\n{output[:500]}"
                    )
                    results.append(
                        f"   💡 Corrección sugerida: {eval_result.get('course_correction_advice', 'Sin consejo')}"
                    )

                # Guardar evaluación en Engram para trazabilidad
                if eval_result:
                    self.engram.save(
                        f"Evaluación paso {i} - {desc}: Score {alignment}",
                        tags=[
                            "step_evaluation",
                            f"spec_{spec['name']}",
                            f"score_{alignment}",
                        ],
                    )

            except Exception as e:
                logger.exception("Error crítico en paso %d: %s", i, skill)
                results.append(f"❌ **Paso {i} - {desc}** falló críticamente: {e}")
                # Podríamos detener la ejecución o continuar. Decidimos continuar.

        # 5. Marcar estado final
        failed_steps = [r for r in results if r.startswith("❌") or r.startswith("⚠️")]
        if failed_steps:
            self.spec_manager.update_status(spec["name"], "completed_with_issues")
        else:
            self.spec_manager.update_status(spec["name"], "completed")

        # 6. Resumen final
        summary = f"## 📋 Ejecución de Spec: {spec['name']}\n\n"
        summary += "\n\n---\n\n".join(results)
        summary += "\n\n---\n\n✅ **Especificación ejecutada.**"

        # Guardar el plan y los resultados en Engram
        self.engram.save(
            f"Plan ejecutado para spec {spec['name']}: {summary[:500]}",
            tags=["plan_execution", f"spec_{spec['name']}", "sdd"],
        )

        return summary

    def _generate_plan_from_spec(self, spec: dict, context: dict) -> list:
        """
        Genera un plan detallado (lista de pasos) a partir de la Spec.
        """
        provider, fallback_chain = ProviderSelector.select(
            task="plan_generation", skill_name="plan"
        )
        prompt = f"""
Eres un planificador de desarrollo. A partir de la siguiente especificación (Spec), genera un plan detallado de pasos ejecutables.

Spec:
{json.dumps(spec, ensure_ascii=False, indent=2)}

Contexto adicional: {context or "No hay contexto adicional."}

El plan debe ser una lista de objetos, cada uno con:
- description: descripción del paso
- skill: nombre de la skill (shell, code, analyze, docker, laravel_project, etc.)
- params: diccionario de parámetros para la skill

Devuelve SOLO un JSON con la lista de pasos.
Ejemplo:
[
  {{"description": "Crear modelo de usuario", "skill": "code", "params": {{"task": "Genera modelo User", "language": "python"}}}},
  {{"description": "Crear endpoint de registro", "skill": "code", "params": {{"task": "Crea endpoint /register", "language": "python"}}}}
]
"""
        try:
            response = self.provider_manager.generate(
                prompt, provider_name=provider, fallback_chain=fallback_chain
            )
            start = response.find("[")
            end = response.rfind("]") + 1
            if start != -1 and end != -1:
                plan = json.loads(response[start:end])
                return plan
            else:
                raise ValueError("No se encontró JSON en la respuesta")
        except Exception as e:
            logger.exception("Error generando plan: %s", e)
            return None

    def _should_critic_step(self, step: dict, result: any) -> bool:
        """Decide si un paso merece ser evaluado por SelfCritic."""
        # Evaluar solo pasos importantes (code, analyze, project)
        skill = step.get("skill")
        if skill in (
            "code",
            "analyze",
            "analyze_project",
            "laravel_project",
            "full_project",
        ):
            return True
        return False

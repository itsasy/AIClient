import json
import logging

from agents.base import Agent
from llm.provider_manager import ProviderManager
from llm.provider_selector import ProviderSelector
from skills.manager import SkillManager

logger = logging.getLogger(__name__)


class PlannerAgent(Agent):
    name = "planner"
    role = "Planificador y Ejecutor Autónomo"

    def __init__(self):
        self.skill_manager = SkillManager()
        self.provider_manager = ProviderManager()

    def process(
        self,
        task: str,
        context: dict = None,
        skill_name: str = None,
        skill_params: dict = None,
    ) -> str:
        # 1. Generar el plan usando el LLM directamente (sin detección de skills)
        selected_provider = ProviderSelector.select(task=task, skill_name="plan")

        prompt = f"""Eres un planificador autónomo. Descompón la siguiente tarea en pasos ejecutables utilizando las skills disponibles.

Skills disponibles: shell, docker, laravel_project, full_project, analyze, code, readme, analyze_project, execute_code, sandbox.

Tarea: {task}

Contexto adicional:
{context or "No hay contexto adicional."}

Devuelve SOLO un JSON válido con una lista de objetos con el siguiente formato:
[
    {{"skill": "shell", "params": {{"command": "ls -la"}}, "description": "Listar archivos del directorio"}},
    {{"skill": "code", "params": {{"task": "genera una función de suma", "language": "python"}}, "description": "Generar código"}},
    {{"skill": "analyze", "params": {{"code_snippet": "def foo(): pass"}}, "description": "Analizar el código"}}
]

REGLAS:
- Usa SOLO las skills listadas arriba.
- Cada paso debe tener una descripción clara.
- Si la tarea es simple, devuelve un solo paso.
- Si es compleja, divídela en pasos lógicos y secuenciales.
- No incluyas texto adicional fuera del JSON.
- Asegúrate de que el JSON sea válido.
"""
        try:
            plan_text = self.provider_manager.generate(
                prompt, provider_name=selected_provider
            )

            # Extraer el JSON del texto (por si el LLM añade markdown o explicaciones)
            start = plan_text.find("[")
            end = plan_text.rfind("]") + 1
            if start != -1 and end != -1:
                plan_text = plan_text[start:end]

            plan = json.loads(plan_text)
            if not isinstance(plan, list):
                raise ValueError("El plan no es una lista de pasos.")

        except Exception as e:
            logger.exception("Error generando o parseando el plan")
            return f"❌ No se pudo generar un plan para la tarea.\nError: {e}\n\nRespuesta del LLM:\n{plan_text if 'plan_text' in locals() else 'Sin respuesta'}"

        # 2. Ejecutar cada paso secuencialmente
        results = []
        for i, step in enumerate(plan, 1):
            skill = step.get("skill")
            params = step.get("params", {})
            desc = step.get("description", f"Paso {i}: {skill}")

            if not skill:
                results.append(f"⚠️ **Paso {i}**: Skill no especificada. Saltando.")
                continue

            logger.info("Ejecutando paso %d: %s (%s)", i, desc, skill)

            try:
                result = self.skill_manager.execute(skill, **params)
                # Extraer la salida legible del resultado
                if isinstance(result, dict):
                    payload = result.get("payload", {})
                    output = (
                        payload.get("output") or payload.get("message") or str(result)
                    )
                else:
                    output = str(result)

                results.append(
                    f"✅ **Paso {i} - {desc}**\n{output[:500]}"
                )  # Limitar a 500 chars

            except Exception as e:
                logger.exception("Error ejecutando paso %d: %s", i, skill)
                results.append(f"❌ **Paso {i} - {desc}** falló: {e}")
                # Detener la ejecución en caso de error grave (opcional)
                # break

        # 3. Generar resumen final
        if not results:
            return "⚠️ No se generaron pasos para ejecutar."

        summary = "## 📋 Plan ejecutado autónomamente\n\n"
        summary += "\n\n---\n\n".join(results)
        summary += "\n\n---\n\n✅ **Ejecución completada.**"

        return summary

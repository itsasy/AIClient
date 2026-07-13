class PromptBuilder:
    @staticmethod
    def build(
        task: str,
        context=None,
        skill_name=None,
        skill_result=None,
    ) -> str:
        context_text = PromptBuilder._format_context(context)

        base = f"""
Eres un asistente senior de desarrollo de software.

Consulta del usuario:

{task}

Contexto disponible:

{context_text}
""".strip()

        if not skill_name or not skill_result:
            return base

        if not isinstance(skill_result, dict):
            return f"""
{base}

Resultado de la skill:

{skill_result}
""".strip()

        skill_type = skill_result.get("type")
        payload = skill_result.get("payload", {})

        if skill_type == "code_generation":
            task_to_generate = payload.get("task", "")
            language = payload.get("language", "python")

            return f"""
{base}

Genera código para:

{task_to_generate}

Lenguaje:

{language}

Entrega una solución concreta, limpia y lista para usar.
No inventes requisitos que no aparezcan en la solicitud.
""".strip()

        if skill_type == "code_analysis":
            code = payload.get("code", "")
            language = payload.get("language", "python")

            return f"""
{base}

Analiza el siguiente código.

Lenguaje:

{language}

Código:

{code}

Evalúa:

- bugs y errores potenciales
- seguridad
- buenas prácticas
- principios SOLID cuando correspondan
- rendimiento
- mantenibilidad
- oportunidades de refactorización

Distingue claramente entre problemas reales y mejoras opcionales.
No inventes código que no haya sido proporcionado.
""".strip()

        if skill_type == "project_analysis":
            snapshot = payload if isinstance(payload, str) else str(payload)

            return f"""
{base}

Analiza el proyecto actual utilizando la evidencia inspeccionada.

Snapshot del proyecto:

{snapshot}

Evalúa:

- arquitectura
- modularidad
- dependencias
- organización
- calidad del código
- posibles bugs
- seguridad
- deuda técnica
- oportunidades de mejora

REGLAS:

- Analiza únicamente la información disponible.
- No afirmes haber inspeccionado archivos que no aparecen en el snapshot.
- Distingue entre problemas confirmados, riesgos potenciales y recomendaciones.
- Cita los archivos concretos cuando la evidencia permita identificar su origen.
- No solicites al usuario que pegue código que ya aparece en el snapshot.
""".strip()

        if skill_type == "readme":
            snapshot = payload.get("snapshot", "")
            request = payload.get(
                "request",
                payload.get("requested_name", ""),
            )
            description = payload.get("description", "")

            return f"""
{base}

Genera un README profesional para el proyecto solicitado.

Solicitud:

{request}

Descripción proporcionada:

{description or "No proporcionada."}

Información verificada del proyecto:

{snapshot}

REGLAS OBLIGATORIAS:

- Usa únicamente información verificable en el contexto y snapshot.
- No inventes funcionalidades.
- No inventes repositorios ni URLs.
- No inventes autores, emails ni datos de contacto.
- No inventes licencias.
- No inventes una fase o estado del proyecto.
- No menciones archivos que no aparezcan en la información disponible.
- Distingue claramente entre funcionalidades actuales y objetivos futuros.
- Si un dato no está disponible, simplemente omítelo.
- No uses placeholders como "tu_usuario", "tu_email" o "example.com".
- El resultado debe poder utilizarse directamente como README.md.
""".strip()

        return base

    @staticmethod
    def _format_context(context) -> str:
        if not context:
            return "No hay contexto adicional disponible."

        if not isinstance(context, dict):
            return str(context)

        sections = []

        project = context.get("project")
        if project:
            sections.append(
                f"=== PROYECTO ===\n{project}"
            )

        obsidian = context.get("obsidian")
        if obsidian:
            sections.append(
                f"=== CONOCIMIENTO LOCAL / OBSIDIAN ===\n{obsidian}"
            )

        memory = context.get("memory")
        if memory:
            sections.append(
                f"=== MEMORIA DE CONVERSACIÓN ===\n{memory}"
            )

        query = context.get("query")
        if query:
            sections.append(
                f"=== CONSULTA ACTUAL ===\n{query}"
            )

        if not sections:
            return str(context)

        return "\n\n".join(sections)
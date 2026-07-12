class PromptBuilder:
    @staticmethod
    def build(
        task: str,
        context,
        skill_name=None,
        skill_result=None,
    ) -> str:
        context_text = PromptBuilder._format_context(context)

        base = f"""
Eres un asistente senior de desarrollo de software.

CONSULTA DEL USUARIO:
{task}

CONTEXTO DISPONIBLE:
{context_text}
""".strip()

        if not skill_name or not skill_result:
            return base

        skill_type = skill_result.get("type")
        payload = skill_result.get("payload", {})

        if skill_type == "code_generation":
            return f"""
{base}

TAREA:
Genera una solución para:

{payload.get("task", task)}

Lenguaje preferido:
{payload.get("language", "python")}

Entrega una solución concreta, moderna y lista para usar.
No inventes requisitos que no hayan sido proporcionados.
""".strip()

        if skill_type == "code_analysis":
            return f"""
{base}

TAREA:
Analiza exclusivamente el siguiente código:

{payload.get("code", "")}

Evalúa:

- bugs
- seguridad
- buenas prácticas
- SOLID
- rendimiento
- oportunidades de refactorización

No confundas la consulta del usuario con código fuente.
""".strip()

        if skill_type == "project_analysis":
            return f"""
{base}

TAREA:
Analiza el proyecto actual usando el siguiente snapshot:

{payload}

Evalúa:

- arquitectura
- estructura
- modularidad
- responsabilidades
- dependencias
- deuda técnica
- problemas potenciales
- oportunidades de mejora

No solicites al usuario que copie archivos que ya aparecen en el snapshot.
No inventes contenido de archivos que no haya sido inspeccionado.
Distingue claramente entre hechos observados y recomendaciones.
""".strip()

        if skill_type == "readme":
            return f"""
{base}

TAREA:
Genera un README profesional para el proyecto.

Información:

{payload}
""".strip()

        return base

    @staticmethod
    def _format_context(context) -> str:
        if not isinstance(context, dict):
            return str(context or "")

        sections = []

        if context.get("project"):
            sections.append(
                f"=== PROYECTO ===\n{context['project']}"
            )

        if context.get("obsidian"):
            sections.append(
                f"=== OBSIDIAN ===\n{context['obsidian']}"
            )

        if context.get("memory"):
            sections.append(
                f"=== MEMORIA RECIENTE ===\n{context['memory']}"
            )

        return "\n\n".join(sections)
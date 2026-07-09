class PromptBuilder:
    _registry = {
        "code_generation": """
{base}

Genera código para:

{payload.get('task', '')}

Lenguaje:

{payload.get('language', 'python')}

Entrega únicamente una solución lista para usar.
""",
        "code_analysis": """
{base}

Analiza este código.

Código:

{payload.get('code', '')}

Busca:

- bugs
- seguridad
- SOLID
- rendimiento
- refactor
""",
        "project_analysis": """
{base}

Analiza este proyecto completo.

Proyecto:

{payload}

Evalúa:

- arquitectura
- modularidad
- dependencias
- organización
- deuda técnica
- oportunidades de mejora

No inventes información.
Analiza únicamente lo que aparece en el snapshot.
""",
        "readme": """
{base}

Genera un README profesional usando esta información:

{payload}
""",
    }

    @staticmethod
    def build(task, context, skill_name=None, skill_result=None):
        context_text = PromptBuilder._format_context(context)
        base = f"""
Eres un asistente senior de desarrollo.

Consulta:

{task}

Contexto:

{context_text}
"""

        if not skill_name or not skill_result:
            return base

        skill_type = skill_result.get("type")
        payload = skill_result.get("payload", {})

        if skill_type in PromptBuilder._registry:
            return PromptBuilder._registry[skill_type].format(base=base, payload=payload)

        return base

    @staticmethod
    def _format_context(context):
        if isinstance(context, dict):
            sections = []
            if context.get("project"):
                sections.append(f"=== PROYECTO ===\n{context['project']}")
            if context.get("obsidian"):
                sections.append(f"=== OBSIDIAN ===\n{context['obsidian']}")
            if context.get("query"):
                sections.append(f"=== CONSULTA ===\n{context['query']}")
            if context.get("memory"):
                sections.append(f"=== MEMORIA ===\n{context['memory']}")
            return "\n\n".join(sections)
        return str(context)
class PromptBuilder:

    @staticmethod
    def build(task,
              context,
              skill_name=None,
              skill_result=None):

        base = f"""
Eres un asistente senior de desarrollo.

Consulta:

{task}

Contexto:

{context}
"""

        if not skill_name:

            return base

        if skill_name == "code":

            return f"""
{base}

Genera código para:

{skill_result["task"]}

Lenguaje:

{skill_result["language"]}

Entrega únicamente una solución lista para usar.
"""

        if skill_name == "analyze":

            return f"""
{base}

Analiza este código.

Código:

{skill_result["code"]}

Busca:

- bugs
- seguridad
- SOLID
- rendimiento
- refactor
"""

        if skill_name == "analyze_project":

            return f"""
{base}

Analiza este proyecto completo.

Proyecto:

{skill_result["snapshot"]}

Evalúa:

- arquitectura

- modularidad

- dependencias

- organización

- deuda técnica

- oportunidades de mejora

No inventes información.

Analiza únicamente lo que aparece en el snapshot.
"""

        return base
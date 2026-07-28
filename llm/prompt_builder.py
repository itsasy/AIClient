from pathlib import Path

from core.config import Config
from core.context_retriever import ContextRetriever
from core.learner import ContinuousLearner


class PromptBuilder:
    """
    Construye prompts para el LLM combinando:
    - Tarea del usuario
    - Contexto del proyecto (snapshot)
    - Contexto de Obsidian (RAG)
    - Memoria conversacional (historial)
    - Memoria persistente (Engram)
    - Estándares aprendidos (ContinuousLearner)
    - Resultados de skills (si los hay)

    Los prompts se cargan desde archivos de plantilla en `llm/prompts/`.
    """

    PROMPTS_DIR = Config.PROJECT_ROOT / "llm" / "prompts"

    @staticmethod
    def _load_template(name: str) -> str:
        """Carga una plantilla desde la carpeta `llm/prompts/`."""
        path = PromptBuilder.PROMPTS_DIR / f"{name}.txt"
        if not path.exists():
            raise FileNotFoundError(f"Plantilla no encontrada: {path}")
        return path.read_text(encoding="utf-8")

    @staticmethod
    def build(task: str, context=None, skill_name=None, skill_result=None) -> str:
        """
        Construye el prompt final para el LLM.

        Args:
            task (str): Consulta del usuario.
            context (dict, optional): Diccionario con contexto (project, obsidian, engram, memory, etc.).
            skill_name (str, optional): Nombre de la skill detectada.
            skill_result (dict, optional): Resultado de la skill (si se ejecutó).

        Returns:
            str: Prompt listo para enviar al LLM.
        """
        # ------------------------------------------------------------
        # 1. RECUPERAR Y FILTRAR CONTEXTO (ContextRetriever)
        # ------------------------------------------------------------
        context = ContextRetriever.retrieve(context)

        # ------------------------------------------------------------
        # 2. INYECTAR ESTÁNDARES APRENDIDOS (ContinuousLearner)
        # ------------------------------------------------------------
        learner = ContinuousLearner()
        standards = learner.get_context()
        if standards:
            if context is None:
                context = {}
            context["standards"] = standards

        # ------------------------------------------------------------
        # 3. FORMATEAR CONTEXTO PARA EL PROMPT (texto plano)
        # ------------------------------------------------------------
        context_text = PromptBuilder._format_context(context)

        # ------------------------------------------------------------
        # 4. SELECCIONAR PLANTILLA SEGÚN EL TIPO DE SKILL
        # ------------------------------------------------------------
        if not skill_name or not skill_result:
            return PromptBuilder._build_general_prompt(task, context_text)

        skill_type = skill_result.get("type")
        payload = skill_result.get("payload", {})

        if skill_type == "code_generation":
            return PromptBuilder._build_code_generation(task, context_text, payload)
        if skill_type == "code_analysis":
            return PromptBuilder._build_code_analysis(task, context_text, payload)
        if skill_type == "project_analysis":
            return PromptBuilder._build_project_analysis(task, context_text, payload)
        if skill_type == "readme":
            return PromptBuilder._build_readme(task, context_text, payload)

        # Fallback seguro: si el tipo de skill no está contemplado
        return PromptBuilder._build_general_prompt(task, context_text)

    # ------------------------------------------------------------
    # MÉTODOS PRIVADOS: CONSTRUCCIÓN DE PROMPTS POR TIPO
    # ------------------------------------------------------------

    @staticmethod
    def _build_general_prompt(task: str, context_text: str) -> str:
        template = PromptBuilder._load_template("general")
        return template.format(
            task=task,
            context_text=context_text or "No hay contexto adicional relevante.",
        )

    @staticmethod
    def _build_code_generation(task: str, context_text: str, payload: dict) -> str:
        template = PromptBuilder._load_template("code_generation")
        return template.format(
            base_task=task,
            context_text=context_text or "No hay contexto adicional disponible.",
            task=payload.get("task", ""),
            language=payload.get("language", "python"),
        )

    @staticmethod
    def _build_code_analysis(task: str, context_text: str, payload: dict) -> str:
        template = PromptBuilder._load_template("code_analysis")
        return template.format(
            base_task=task,
            context_text=context_text or "No hay contexto adicional disponible.",
            code=payload.get("code", ""),
            language=payload.get("language", "python"),
        )

    @staticmethod
    def _build_project_analysis(task: str, context_text: str, payload) -> str:
        snapshot = (
            payload.get("snapshot", "") if isinstance(payload, dict) else str(payload)
        )
        template = PromptBuilder._load_template("project_analysis")
        return template.format(
            base_task=task,
            context_text=context_text or "No hay contexto adicional disponible.",
            snapshot=snapshot,
        )

    @staticmethod
    def _build_readme(task: str, context_text: str, payload: dict) -> str:
        template = PromptBuilder._load_template("readme")
        return template.format(
            base_task=task,
            context_text=context_text or "No hay contexto adicional disponible.",
            requested_name=payload.get("request", ""),
            description=payload.get("description", "No proporcionada."),
            snapshot=payload.get("snapshot", ""),
        )

    # ------------------------------------------------------------
    # FORMATEO DEL CONTEXTO (convierte dict → texto plano)
    # ------------------------------------------------------------

    @staticmethod
    def _format_context(context) -> str:
        """
        Convierte el diccionario de contexto en texto plano formateado,
        con secciones claramente delimitadas.
        """
        if not context:
            return ""
        if not isinstance(context, dict):
            return str(context)

        sections = []

        # 1. Proyecto (snapshot)
        if context.get("project"):
            sections.append(f"=== PROYECTO ===\n{context['project']}")

        # 2. Obsidian (RAG)
        if context.get("obsidian"):
            sections.append(f"=== OBSIDIAN ===\n{context['obsidian']}")

        # 3. Memoria conversacional (historial reciente)
        if context.get("memory"):
            sections.append(f"=== MEMORIA CONVERSACIONAL ===\n{context['memory']}")

        # 4. Memoria persistente (Engram)
        if context.get("engram"):
            sections.append(f"=== MEMORIA RECUPERADA (Engram) ===\n{context['engram']}")

        # 5. Estándares aprendidos (ContinuousLearner)
        if context.get("standards"):
            sections.append(f"=== ESTÁNDARES APRENDIDOS ===\n{context['standards']}")

        # 6. Archivos relevantes (si los hubiera)
        if context.get("files"):
            sections.append(f"=== ARCHIVOS RELEVANTES ===\n{context['files']}")

        # 7. Arquitectura (si se proporciona explícitamente)
        if context.get("architecture"):
            sections.append(f"=== ARQUITECTURA ===\n{context['architecture']}")

        # 8. Spec / Plan (para tareas de SDD, futuro)
        if context.get("spec"):
            sections.append(f"=== SPEC / PLAN ===\n{context['spec']}")

        return "\n\n".join(sections)

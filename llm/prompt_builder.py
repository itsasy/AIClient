from pathlib import Path
from core.config import Config
from core.context_retriever import ContextRetriever


class PromptBuilder:
    PROMPTS_DIR = Config.PROJECT_ROOT / "prompts"

    @staticmethod
    def _load_template(name: str) -> str:
        path = PromptBuilder.PROMPTS_DIR / f"{name}.txt"
        if not path.exists():
            raise FileNotFoundError(f"Plantilla no encontrada: {path}")
        return path.read_text(encoding="utf-8")

    @staticmethod
    def build(task: str, context=None, skill_name=None, skill_result=None) -> str:
        context = ContextRetriever.retrieve(context)
        context_text = PromptBuilder._format_context(context)

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

        return PromptBuilder._build_general_prompt(task, context_text)

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

    @staticmethod
    def _format_context(context) -> str:
        if not context:
            return ""
        if not isinstance(context, dict):
            return str(context)

        sections = []
        if context.get("project"):
            sections.append(f"=== PROYECTO ===\n{context['project']}")
        if context.get("obsidian"):
            sections.append(f"=== OBSIDIAN ===\n{context['obsidian']}")
        if context.get("memory"):
            sections.append(f"=== MEMORIA ===\n{context['memory']}")
        if context.get("files"):
            sections.append(f"=== ARCHIVOS RELEVANTES ===\n{context['files']}")
        if context.get("architecture"):
            sections.append(f"=== ARQUITECTURA ===\n{context['architecture']}")
        return "\n\n".join(sections)

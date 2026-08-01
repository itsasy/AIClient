import logging
from typing import Dict, Any

from core.execution_plan import ExecutionPlan
from core.project_inspector import ProjectInspector
from core.engram_memory import EngramMemory
from core.memory import ConversationMemory
from obsidian.rag import RAG
from core.document_ingestor import DocumentIngestor
from core.gentleman_skills import GentlemanSkills

logger = logging.getLogger(__name__)


class ContextProvider:
    """
    Construye contexto bajo demanda según ExecutionPlan.

    Responsabilidades:
    - Cargar solo los proveedores solicitados.
    - No tomar decisiones de negocio.
    - Devolver un diccionario con el contexto listo para usar.
    """

    def __init__(self):
        self.project_inspector = ProjectInspector()
        self.engram = EngramMemory()
        self.memory = ConversationMemory()
        self.rag = RAG()
        self.ingestor = DocumentIngestor()
        self.gentleman = GentlemanSkills()

    def build(self, plan: ExecutionPlan) -> Dict[str, Any]:
        """
        Construye el contexto basado en las necesidades del plan.
        """
        context: Dict[str, Any] = {}

        # 1. Proyecto (snapshot)
        if plan.requires_context("project"):
            try:
                context["project"] = self.project_inspector.inspect()
                logger.debug("Contexto de proyecto cargado")
            except Exception as e:
                logger.warning("Error cargando proyecto: %s", e)
                context["project"] = "No se pudo inspeccionar el proyecto."

        # 2. Memoria persistente (Engram)
        if plan.requires_context("engram"):
            try:
                engram_data = self.engram.get_context(plan.original_task, limit=3)
                if engram_data:
                    context["engram"] = engram_data
                    logger.debug("Contexto de Engram cargado")
            except Exception as e:
                logger.warning("Error cargando Engram: %s", e)

        # 3. Memoria conversacional (historial)
        if plan.requires_context("memory"):
            try:
                memory_data = self.memory.get_context()
                if memory_data:
                    context["memory"] = memory_data
                    logger.debug("Contexto de memoria conversacional cargado")
            except Exception as e:
                logger.warning("Error cargando memoria: %s", e)

        # 4. Obsidian (RAG)
        if plan.requires_context("obsidian"):
            try:
                obsidian_data = self.rag.get_relevant_context(plan.original_task, max_results=5)
                if obsidian_data:
                    context["obsidian"] = obsidian_data
                    logger.debug("Contexto de Obsidian cargado")
            except Exception as e:
                logger.warning("Error cargando Obsidian: %s", e)

        # 5. Documentos ingeridos
        if plan.requires_context("documents"):
            try:
                docs = self.ingestor.list_ingested()
                if docs:
                    doc_list = "\n".join(
                        [f"- {d['name']} ({d['chunks']} fragmentos)" for d in docs]
                    )
                    context["documents"] = f"=== DOCUMENTOS INGERIDOS ===\n{doc_list}"
                    logger.debug("Contexto de documentos cargado")
            except Exception as e:
                logger.warning("Error cargando documentos: %s", e)

        # 6. Estándares aprendidos (ContinuousLearner)
        if plan.requires_context("standards"):
            try:
                from core.learner import ContinuousLearner

                learner = ContinuousLearner()
                standards = learner.get_context()
                if standards:
                    context["standards"] = standards
                    logger.debug("Contexto de estándares cargado")
            except Exception as e:
                logger.warning("Error cargando estándares: %s", e)

        # 7. Estándares aprendidos (ContinuousLearner)
        if plan.requires_context("gentleman"):
            relevant = self.gentleman.find_relevant(plan.original_task)
            if relevant:
                skills_text = "\n\n".join(
                    [f"## Skill: {name}\n{self.gentleman.get_skill(name)}" for name in relevant[:3]]
                )
                context["gentleman_skills"] = (
                    f"=== SKILLS DE GENTLEMAN (contexto) ===\n{skills_text}"
                )

                logger.info("Contexto construido con: %s", list(context.keys()))
        return context

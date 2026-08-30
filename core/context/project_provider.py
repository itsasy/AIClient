from typing import Any

from core.context.base import BaseContextProvider
from core.execution_plan import ExecutionPlan
from core.project_inspector import ProjectInspector


class ProjectProvider(BaseContextProvider):

    key = "project"
    name = "Project Context"
    description = "Inspección estructural del proyecto objetivo."

    def __init__(self) -> None:
        self.inspector = ProjectInspector()

    def load(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
    ) -> dict[str, Any]:

        snapshot = self.inspector.inspect_snapshot()
        from core.discovery.engine import DiscoveryEngine
        from core.discovery.understanding import UnderstandingEngine
        from core.discovery.analysis import AnalysisEngine
        from core.discovery.task_analysis import TaskReuseAnalyzer
        from core.discovery.context_selection import ContextSelector
        from core.discovery.transformation import TransformationPlanner
        from core.discovery.transformation_policy import TransformationPolicyEvaluator
        from core.skills.discovery import SkillDiscovery
        from core.skills.registry import SkillRegistry
        from core.config import Config
        root = Config.TARGET_PROJECT_ROOT.expanduser().resolve()
        
        env = DiscoveryEngine(root).discover()
        understanding = UnderstandingEngine(root, env).analyze()
        analysis = AnalysisEngine(root, env, understanding).analyze()
        
        task = plan.objective or plan.original_task or ""
        task_analysis = TaskReuseAnalyzer(task, understanding, analysis).analyze()
        
        transformation = TransformationPlanner(
            root, env, understanding, analysis, task_analysis
        ).plan()
        
        policy = TransformationPolicyEvaluator(transformation).evaluate()
        
        # Skill Registry setup
        skill_discovery = SkillDiscovery([str(Config.APP_DATA_DIR / "builtin" / "skills")])
        registry = SkillRegistry()
        registry.load_from_discovery(skill_discovery)
        
        # The complete Project Knowledge
        knowledge = {
            "snapshot": snapshot.to_architecture_context(),
            "environment": env.to_dict(),
            "understanding": understanding.to_dict(),
            "coupling_analysis": [b.to_dict() for b in analysis.boundaries],
            "reuse_analysis": [r.to_dict() for r in analysis.reuse_analysis],
            "task_analysis": task_analysis.to_dict() if task else None,
            "transformation_plan": transformation.to_dict(),
            "transformation_policy": policy.to_dict(),
            "skills_available": [s.to_dict() for s in registry.get_all()]
        }
        
        # Capability Match injected for context mapping later
        knowledge["capability_matches"] = {}
        if task_analysis:
            for cand in task_analysis.relevant_candidates:
                # Naive requirement for testing P8 match
                match = registry.match_capabilities(cand.module, ["move_files", "rewrite_imports"])
                knowledge["capability_matches"][cand.module] = match.to_dict()
        
        # LLM Context generated via Selector
        selector = ContextSelector(plan=plan, budget=12000)
        return selector.select(knowledge)

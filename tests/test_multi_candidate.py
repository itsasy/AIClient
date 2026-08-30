import pytest
from core.discovery.transformation import MultiCandidateTransformationPlan, CandidateTransformationPlan, ExtractionAction
from core.execution.global_workflow import GlobalWorkflowPlanner
from core.discovery.transformation_policy import TransformationPolicy, PolicyDecision
from core.skills.registry import SkillRegistry
from core.skills.models import Skill

def test_global_workflow_success(tmp_path):
    plan = MultiCandidateTransformationPlan("tx_1", target_root=str(tmp_path))
    c1 = CandidateTransformationPlan("auth", classification="REUSABLE", extraction_readiness="READY", recommendation="reuse")
    c1.actions.append(ExtractionAction("move_files", source="a.py", destination="shared/a.py"))
    c1.boundary.include.append("a.py")
    
    c2 = CandidateTransformationPlan("users", classification="REUSABLE", extraction_readiness="READY", recommendation="reuse")
    c2.actions.append(ExtractionAction("move_files", source="u.py", destination="shared/u.py"))
    c2.boundary.include.append("u.py")
    
    plan.candidates = [c1, c2]
    plan.calculate_global_boundary()
    
    policy = TransformationPolicy([
        PolicyDecision("auth", "ALLOW", ["move_files"], [], []),
        PolicyDecision("users", "ALLOW", ["move_files"], [], [])
    ])
    registry = SkillRegistry()
    registry.register(Skill("reuse_extraction", "loc", "desc", ["move_files"], [], True, True))
    
    planner = GlobalWorkflowPlanner(str(tmp_path), policy, registry)
    gwf = planner.build(plan)
    
    assert gwf.status == "READY"
    assert "auth" in gwf.candidate_workflows
    assert "users" in gwf.candidate_workflows
    assert gwf.global_workflow_hash != ""

def test_global_workflow_circular_dependency(tmp_path):
    plan = MultiCandidateTransformationPlan("tx_1", target_root=str(tmp_path))
    c1 = CandidateTransformationPlan("auth", classification="REUSABLE", extraction_readiness="READY", recommendation="reuse")
    c1.dependencies.append("users")
    c2 = CandidateTransformationPlan("users", classification="REUSABLE", extraction_readiness="READY", recommendation="reuse")
    c2.dependencies.append("auth")
    plan.candidates = [c1, c2]
    
    policy = TransformationPolicy([
        PolicyDecision("auth", "ALLOW", [], [], []),
        PolicyDecision("users", "ALLOW", [], [], [])
    ])
    registry = SkillRegistry()
    
    planner = GlobalWorkflowPlanner(str(tmp_path), policy, registry)
    gwf = planner.build(plan)
    
    assert gwf.status == "BLOCKED"
    assert "circular_dependency" in gwf.reason

def test_global_workflow_destination_conflict(tmp_path):
    plan = MultiCandidateTransformationPlan("tx_1", target_root=str(tmp_path))
    c1 = CandidateTransformationPlan("auth", classification="REUSABLE", extraction_readiness="READY", recommendation="reuse")
    c1.actions.append(ExtractionAction("move_files", source="a.py", destination="shared/conflict.py"))
    c1.boundary.include.append("a.py")
    
    c2 = CandidateTransformationPlan("users", classification="REUSABLE", extraction_readiness="READY", recommendation="reuse")
    c2.actions.append(ExtractionAction("move_files", source="u.py", destination="shared/conflict.py"))
    c2.boundary.include.append("u.py")
    
    plan.candidates = [c1, c2]
    plan.calculate_global_boundary()
    
    policy = TransformationPolicy([
        PolicyDecision("auth", "ALLOW", ["move_files"], [], []),
        PolicyDecision("users", "ALLOW", ["move_files"], [], [])
    ])
    registry = SkillRegistry()
    registry.register(Skill("reuse_extraction", "loc", "desc", ["move_files"], [], True, True))
    
    planner = GlobalWorkflowPlanner(str(tmp_path), policy, registry)
    gwf = planner.build(plan)
    
    assert gwf.status == "BLOCKED"
    assert "DESTINATION_CONFLICT" in gwf.reason

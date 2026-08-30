import pytest
import uuid
import hashlib
from core.discovery.transformation import MultiCandidateTransformationPlan, CandidateTransformationPlan, ExtractionAction
from core.execution.global_workflow import GlobalWorkflowPlanner
from core.discovery.transformation_policy import TransformationPolicy, PolicyDecision
from core.skills.registry import SkillRegistry
from core.skills.models import Skill
from core.execution.orchestrator import TransformationOrchestrator
from core.execution.approval import ApprovalLifecycleManager

def test_global_transaction_all_pass(tmp_path):
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
        PolicyDecision("auth", "ALLOW", [], ["move_files"], []),
        PolicyDecision("users", "ALLOW", [], ["move_files"], [])
    ])
    registry = SkillRegistry()
    registry.register(Skill("reuse_extraction", "loc", "desc", ["move_files"], [], True, True))
    
    (tmp_path / "a.py").write_text("code a")
    (tmp_path / "u.py").write_text("code u")
    
    planner = GlobalWorkflowPlanner(str(tmp_path), policy, registry)
    gwf = planner.build(plan)
    
    app_mgr = ApprovalLifecycleManager()
    approval = app_mgr.request_approval(plan.transaction_id, "GLOBAL", gwf.global_workflow_hash, "phash", "bhash", ["move_files"])
    app_mgr.approve(approval.approval_id)
    
    orch = TransformationOrchestrator(tmp_path, plan, policy, registry, approvals={"auth": ["move_files"], "users": ["move_files"]})
    record = orch.execute_global_workflow(gwf, approval, app_mgr, mode="EXECUTE")
    if record.status != "COMMITTED":
        print(f"ERRORS: {record.errors}")
    
    assert record.status == "COMMITTED"
    assert (tmp_path / "shared/a.py").exists()
    assert (tmp_path / "shared/u.py").exists()
    assert not (tmp_path / "a.py").exists()
    assert not (tmp_path / "u.py").exists()

def test_global_transaction_partial_fail_rolls_back_all(tmp_path):
    plan = MultiCandidateTransformationPlan("tx_2", target_root=str(tmp_path))
    c1 = CandidateTransformationPlan("auth", classification="REUSABLE", extraction_readiness="READY", recommendation="reuse")
    c1.actions.append(ExtractionAction("move_files", source="a.py", destination="shared/a.py"))
    c1.boundary.include.append("a.py")
    
    c2 = CandidateTransformationPlan("users", classification="REUSABLE", extraction_readiness="READY", recommendation="reuse")
    c2.actions.append(ExtractionAction("move_files", source="missing.py", destination="shared/missing.py"))
    c2.boundary.include.append("missing.py")
    
    plan.candidates = [c1, c2]
    plan.calculate_global_boundary()
    
    policy = TransformationPolicy([
        PolicyDecision("auth", "ALLOW", [], ["move_files"], []),
        PolicyDecision("users", "ALLOW", [], ["move_files"], [])
    ])
    registry = SkillRegistry()
    registry.register(Skill("reuse_extraction", "loc", "desc", ["move_files"], [], True, True))
    
    (tmp_path / "a.py").write_text("code a")
    # intentionally not creating missing.py so c2 fails
    
    planner = GlobalWorkflowPlanner(str(tmp_path), policy, registry)
    gwf = planner.build(plan)
    
    app_mgr = ApprovalLifecycleManager()
    approval = app_mgr.request_approval(plan.transaction_id, "GLOBAL", gwf.global_workflow_hash, "phash", "bhash", ["move_files"])
    app_mgr.approve(approval.approval_id)
    
    orch = TransformationOrchestrator(tmp_path, plan, policy, registry, approvals={"auth": ["move_files"], "users": ["move_files"]})
    record = orch.execute_global_workflow(gwf, approval, app_mgr, mode="EXECUTE")
    
    assert record.status == "ROLLED_BACK"
    assert (tmp_path / "a.py").exists() # Rolled back!
    assert not (tmp_path / "shared/a.py").exists()

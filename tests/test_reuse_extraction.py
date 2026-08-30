import pytest
from pathlib import Path
import time
import uuid

from core.discovery.transformation import TransformationPlan, MultiCandidateTransformationPlan, CandidateTransformationPlan, ExtractionBoundary, ExtractionAction
from core.discovery.transformation_policy import TransformationPolicy, PolicyDecision
from core.skills.registry import SkillRegistry
from core.skills.models import Skill
from core.execution.workflow import ExtractionWorkflowPlanner
from core.execution.approval import ApprovalRecord, ApprovalLifecycleManager
from core.execution.orchestrator import TransformationOrchestrator
from core.skills.reuse_extraction import ReuseExtractionSkill

def setup_environment(tmp_path):
    plan = MultiCandidateTransformationPlan("tx_1", candidates=[
        CandidateTransformationPlan(
            candidate="auth",
            classification="REUSABLE",
            extraction_readiness="READY",
            recommendation="reuse",
            boundary=ExtractionBoundary(include=["modules/auth/service.py", "modules/auth/test_service.py"], forbidden=["modules/db/config.py"]),
            actions=[
                ExtractionAction(operation="move_files", source="modules/auth/service.py", destination="shared/auth/service.py")
            ]
        ),
        CandidateTransformationPlan(
            candidate="db",
            classification="COUPLED",
            extraction_readiness="BLOCKED",
            recommendation="do_not_reuse",
            actions=[ExtractionAction(operation="move_files", source="modules/db.py", destination="shared/db.py")]
        )
    ])
    policy = TransformationPolicy(decisions=[
        PolicyDecision(
            candidate="auth",
            decision="ALLOW_WITH_VALIDATION",
            allowed=["inspect_boundary"],
            approval_required=["move_files", "rewrite_imports", "create_declared_adapter"],
            denied=["delete_source"]
        ),
        PolicyDecision(
            candidate="db",
            decision="DENY",
            allowed=[],
            approval_required=[],
            denied=["move_files"]
        )
    ])
    
    registry = SkillRegistry()
    registry.register(Skill("reuse_extraction", "loc", "desc", ["move_files", "rewrite_imports", "create_declared_adapter", "ast_rewrite"], [], True, True))
    
    (tmp_path / "modules" / "auth").mkdir(parents=True, exist_ok=True)
    (tmp_path / "modules" / "auth" / "service.py").write_text("code")
    (tmp_path / "modules" / "auth" / "test_service.py").write_text("test")
    (tmp_path / "modules" / "users").mkdir(parents=True, exist_ok=True)
    (tmp_path / "modules" / "users" / "service.py").write_text("from modules.auth.service import AuthService")
    
    return plan, policy, registry

def test_case_a_simple_extraction(tmp_path):
    plan, policy, registry = setup_environment(tmp_path)
    planner = ExtractionWorkflowPlanner(str(tmp_path), policy, registry)
    workflow = planner.build(plan.candidates[0])
    
    mgr = ApprovalLifecycleManager()
    approval = mgr.request_approval("tx1", "auth", workflow.workflow_hash, "phash", "bhash", ["move_files"])
    mgr.approve(approval.approval_id)
    
    orch = TransformationOrchestrator(tmp_path, plan, policy, registry, approvals={"auth": ["move_files"]})
    skill = ReuseExtractionSkill(orch, policy, registry, approvals={"auth": ["move_files"]})
    
    record = skill.execute(workflow, approval, mgr, mode="EXECUTE")
    assert record.status == "COMMITTED"

def test_case_b_dry_run(tmp_path):
    plan, policy, registry = setup_environment(tmp_path)
    planner = ExtractionWorkflowPlanner(str(tmp_path), policy, registry)
    workflow = planner.build(plan.candidates[0])
    mgr = ApprovalLifecycleManager()
    approval = mgr.request_approval("tx1", "auth", workflow.workflow_hash, "phash", "bhash", ["move_files"])
    mgr.approve(approval.approval_id)
    
    orch = TransformationOrchestrator(tmp_path, plan, policy, registry, approvals={"auth": ["move_files"]})
    skill = ReuseExtractionSkill(orch, policy, registry, approvals={"auth": ["move_files"]})
    
    record = skill.execute(workflow, approval, mgr, mode="DRY_RUN")
    assert record.status == "SUCCESS"

def test_case_c_policy_deny(tmp_path):
    plan, policy, registry = setup_environment(tmp_path)
    planner = ExtractionWorkflowPlanner(str(tmp_path), policy, registry)
    workflow = planner.build(plan.candidates[1])
    
    orch = TransformationOrchestrator(tmp_path, plan, policy, registry, approvals={"db": ["move_files"]})
    skill = ReuseExtractionSkill(orch, policy, registry, approvals={"db": ["move_files"]})
    
    record = skill.execute(workflow, None, None, mode="EXECUTE")
    assert record.status == "REJECTED"

def test_case_d_insufficient_approval(tmp_path):
    plan, policy, registry = setup_environment(tmp_path)
    plan.candidates[0].actions.append(ExtractionAction("rewrite_imports", source="modules/users/service.py", target="modules.auth.service", destination="shared.auth.service"))
    plan.candidates[0].boundary.include.append("modules/users/service.py")
    
    planner = ExtractionWorkflowPlanner(str(tmp_path), policy, registry)
    workflow = planner.build(plan.candidates[0])
    
    mgr = ApprovalLifecycleManager()
    approval = mgr.request_approval("tx1", "auth", workflow.workflow_hash, "phash", "bhash", ["move_files"])
    mgr.approve(approval.approval_id)
    
    orch = TransformationOrchestrator(tmp_path, plan, policy, registry, approvals={"auth": ["move_files"]})
    skill = ReuseExtractionSkill(orch, policy, registry, approvals={"auth": ["move_files"]})
    
    record = skill.execute(workflow, approval, mgr, mode="EXECUTE")
    assert record.status == "REJECTED"

def test_case_e_missing_capability(tmp_path):
    plan, policy, registry = setup_environment(tmp_path)
    plan.candidates[0].actions.append(ExtractionAction("ast_rewrite", source="modules/auth/service.py"))
    
    registry.skills.clear()
    registry.register(Skill("reuse_extraction", "loc", "desc", ["move_files", "rewrite_imports", "create_declared_adapter"], [], True, True))
    
    planner = ExtractionWorkflowPlanner(str(tmp_path), policy, registry)
    workflow = planner.build(plan.candidates[0])
    assert workflow.status == "BLOCKED"

def test_case_i_repeated_transformation(tmp_path):
    plan, policy, registry = setup_environment(tmp_path)
    planner = ExtractionWorkflowPlanner(str(tmp_path), policy, registry)
    workflow = planner.build(plan.candidates[0])
    
    mgr = ApprovalLifecycleManager()
    approval1 = mgr.request_approval("tx1", "auth", workflow.workflow_hash, "phash", "bhash", ["move_files"])
    mgr.approve(approval1.approval_id)
    
    orch = TransformationOrchestrator(tmp_path, plan, policy, registry, approvals={"auth": ["move_files"]})
    skill = ReuseExtractionSkill(orch, policy, registry, approvals={"auth": ["move_files"]})
    
    record1 = skill.execute(workflow, approval1, mgr, mode="EXECUTE")
    assert record1.status == "COMMITTED"
    
    approval2 = mgr.request_approval("tx2", "auth", workflow.workflow_hash, "phash", "bhash", ["move_files"])
    mgr.approve(approval2.approval_id)
    record2 = skill.execute(workflow, approval2, mgr, mode="EXECUTE")
    assert record2.status == "ROLLED_BACK" # Under P18, conflict causes rollback

def test_case_j_secret_safety(tmp_path):
    plan, policy, registry = setup_environment(tmp_path)
    plan.candidates[0].actions[0].source = ".env"
    
    planner = ExtractionWorkflowPlanner(str(tmp_path), policy, registry)
    workflow = planner.build(plan.candidates[0])
    mgr = ApprovalLifecycleManager()
    approval = mgr.request_approval("tx1", "auth", workflow.workflow_hash, "phash", "bhash", ["move_files"])
    mgr.approve(approval.approval_id)
    
    orch = TransformationOrchestrator(tmp_path, plan, policy, registry, approvals={"auth": ["move_files"]})
    skill = ReuseExtractionSkill(orch, policy, registry, approvals={"auth": ["move_files"]})
    
    record = skill.execute(workflow, approval, mgr, mode="EXECUTE")
    assert record.status == "REJECTED"

def test_case_k_path_traversal(tmp_path):
    plan, policy, registry = setup_environment(tmp_path)
    plan.candidates[0].actions[0].destination = "../../outside/service.py"
    
    planner = ExtractionWorkflowPlanner(str(tmp_path), policy, registry)
    workflow = planner.build(plan.candidates[0])
    mgr = ApprovalLifecycleManager()
    approval = mgr.request_approval("tx1", "auth", workflow.workflow_hash, "phash", "bhash", ["move_files"])
    mgr.approve(approval.approval_id)
    
    orch = TransformationOrchestrator(tmp_path, plan, policy, registry, approvals={"auth": ["move_files"]})
    skill = ReuseExtractionSkill(orch, policy, registry, approvals={"auth": ["move_files"]})
    
    record = skill.execute(workflow, approval, mgr, mode="EXECUTE")
    assert record.status == "REJECTED"

def test_case_l_adapter_requirement(tmp_path):
    plan, policy, registry = setup_environment(tmp_path)
    plan.candidates[0].adaptation_requirements.append("persistence_adapter")
    plan.candidates[0].actions.append(ExtractionAction("create_declared_adapter", destination="shared/auth/adapter.py"))
    
    planner = ExtractionWorkflowPlanner(str(tmp_path), policy, registry)
    workflow = planner.build(plan.candidates[0])
    mgr = ApprovalLifecycleManager()
    approval = mgr.request_approval("tx1", "auth", workflow.workflow_hash, "phash", "bhash", ["move_files", "create_declared_adapter"])
    mgr.approve(approval.approval_id)
    
    orch = TransformationOrchestrator(tmp_path, plan, policy, registry, approvals={"auth": ["move_files", "create_declared_adapter"]})
    skill = ReuseExtractionSkill(orch, policy, registry, approvals={"auth": ["move_files", "create_declared_adapter"]})
    
    record = skill.execute(workflow, approval, mgr, mode="EXECUTE")
    assert record.status == "COMMITTED"

def test_case_m_unsupported_adaptation(tmp_path):
    plan, policy, registry = setup_environment(tmp_path)
    plan.candidates[0].actions.append(ExtractionAction("create_declared_adapter", destination="shared/auth/adapter.py"))
    
    planner = ExtractionWorkflowPlanner(str(tmp_path), policy, registry)
    workflow = planner.build(plan.candidates[0])
    
    assert workflow.status == "BLOCKED"




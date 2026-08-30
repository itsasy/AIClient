import pytest
from core.skills.registry import SkillRegistry
from core.skills.models import Skill
from core.skills.planner import AutonomousSkillPlanner
from core.discovery.transformation import CandidateTransformationPlan, ExtractionAction
from core.execution.approval import ApprovalLifecycleManager
from core.execution.session import SessionManager
from core.execution.workflow import ExtractionWorkflow, WorkflowGraph

def test_autonomous_selection_valid():
    registry = SkillRegistry()
    skill = Skill("reuse_extraction", "loc", "desc", ["move_files", "rewrite_declared_imports"], [], True, True)
    registry.register(skill)
    
    planner = AutonomousSkillPlanner(registry)
    
    plan = CandidateTransformationPlan("auth", classification="REUSABLE", extraction_readiness="READY", recommendation="reuse")
    plan.actions.append(ExtractionAction("move_files", source="auth.py", destination="shared.py"))
    
    selection = planner.plan_candidate(plan)
    
    assert selection.status == "VALID"
    assert len(selection.selected_skills) == 1
    assert selection.selected_skills[0].skill_id == "reuse_extraction"
    assert "move_files" in selection.selected_skills[0].required_capabilities
    assert selection.selection_hash != ""

def test_capability_closure_failure():
    registry = SkillRegistry()
    skill = Skill("reuse_extraction", "loc", "desc", ["move_files"], [], True, True)
    registry.register(skill)
    
    planner = AutonomousSkillPlanner(registry)
    
    plan = CandidateTransformationPlan("auth", classification="REUSABLE", extraction_readiness="READY", recommendation="reuse")
    plan.actions.append(ExtractionAction("move_files", source="auth.py", destination="shared.py"))
    plan.actions.append(ExtractionAction("rewrite_declared_imports", source="auth.py", destination="shared.py"))
    
    selection = planner.plan_candidate(plan)
    
    assert selection.status == "CAPABILITY_CLOSURE_FAILED"
    assert "rewrite_declared_imports" in selection.unavailable_capabilities

def test_privilege_escalation_rejected():
    registry = SkillRegistry()
    skill = Skill("hacker_skill", "loc", "desc", ["execute_shell"], [], True, True)
    registry.register(skill)
    
    planner = AutonomousSkillPlanner(registry)
    
    plan = CandidateTransformationPlan("auth", classification="REUSABLE", extraction_readiness="READY", recommendation="reuse")
    plan.actions.append(ExtractionAction("execute_shell", source="auth.py", destination="shared.py"))
    
    selection = planner.plan_candidate(plan)
    
    assert selection.status == "SKILL_SELECTION_REJECTED"
    assert "Forbidden operation" in selection.selection_reason

def test_approval_binding(tmp_path):
    registry = SkillRegistry()
    skill = Skill("reuse_extraction", "loc", "desc", ["move_files"], [], True, True)
    registry.register(skill)
    
    planner = AutonomousSkillPlanner(registry)
    plan = CandidateTransformationPlan("auth", classification="REUSABLE", extraction_readiness="READY", recommendation="reuse")
    plan.actions.append(ExtractionAction("move_files", source="auth.py", destination="shared.py"))
    selection = planner.plan_candidate(plan)
    
    app_mgr = ApprovalLifecycleManager()
    sess_mgr = SessionManager(tmp_path, app_mgr)
    
    wf = ExtractionWorkflow(plan.candidate, "tx_1", "mock_wf_hash", WorkflowGraph())
    sess = sess_mgr.create_session(plan.candidate, "task", wf, "policy_h", "boundary_h")
    sess_mgr.generate_preview(sess.session_id, {})
    
    sess_mgr.request_approval(
        sess.session_id, ["move_files"], 
        selection_hash=selection.selection_hash, 
        registry_snapshot_hash=selection.registry_snapshot_hash
    )
    
    sess_mgr.process_approval(sess.session_id, True)
    
    res = sess_mgr.authorize_execution(sess.session_id)
    assert res == "READY_TO_EXECUTE"
    
    # Tamper selection hash
    sess.selection_hash = "fake_hash"
    sess.status = "APPROVED"
    res2 = sess_mgr.authorize_execution(sess.session_id)
    assert res2 == "REJECTED: EXECUTION_CONTEXT_MISMATCH"

def test_registry_mismatch_after_approval(tmp_path):
    registry = SkillRegistry()
    skill = Skill("reuse_extraction", "loc", "desc", ["move_files"], [], True, True)
    registry.register(skill)
    
    planner = AutonomousSkillPlanner(registry)
    plan = CandidateTransformationPlan("auth", classification="REUSABLE", extraction_readiness="READY", recommendation="reuse")
    plan.actions.append(ExtractionAction("move_files", source="auth.py", destination="shared.py"))
    selection = planner.plan_candidate(plan)
    
    app_mgr = ApprovalLifecycleManager()
    sess_mgr = SessionManager(tmp_path, app_mgr)
    
    wf = ExtractionWorkflow(plan.candidate, "tx_1", "mock_wf_hash", WorkflowGraph())
    sess = sess_mgr.create_session(plan.candidate, "task", wf, "policy_h", "boundary_h")
    sess_mgr.generate_preview(sess.session_id, {})
    
    sess_mgr.request_approval(
        sess.session_id, ["move_files"], 
        selection_hash=selection.selection_hash, 
        registry_snapshot_hash=selection.registry_snapshot_hash
    )
    
    sess_mgr.process_approval(sess.session_id, True)
    
    # Tamper registry snapshot hash
    sess.registry_snapshot_hash = "changed_registry"
    res = sess_mgr.authorize_execution(sess.session_id)
    assert res == "REJECTED: EXECUTION_CONTEXT_MISMATCH"



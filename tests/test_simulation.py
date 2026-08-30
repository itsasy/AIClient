import pytest
from core.discovery.transformation import MultiCandidateTransformationPlan, CandidateTransformationPlan, ExtractionAction
from core.execution.global_workflow import GlobalWorkflowPlanner
from core.discovery.transformation_policy import TransformationPolicy, PolicyDecision
from core.skills.registry import SkillRegistry
from core.skills.models import Skill
from core.execution.simulation import SimulationEngine, SimulationResult, ImpactComparison
from core.execution.approval import ApprovalLifecycleManager
from core.execution.orchestrator import TransformationOrchestrator

def build_test_plan(tmp_path):
    plan = MultiCandidateTransformationPlan("tx_sim", target_root=str(tmp_path))
    c1 = CandidateTransformationPlan("auth", classification="REUSABLE", extraction_readiness="READY", recommendation="reuse")
    c1.actions.append(ExtractionAction("move_files", source="auth.py", destination="shared/auth.py"))
    c1.boundary.include.append("auth.py")
    
    c2 = CandidateTransformationPlan("users", classification="REUSABLE", extraction_readiness="READY", recommendation="reuse")
    c2.actions.append(ExtractionAction("move_files", source="users.py", destination="shared/users.py"))
    c2.boundary.include.append("users.py")
    
    plan.candidates = [c1, c2]
    plan.calculate_global_boundary()
    return plan

def test_simulation_read_only(tmp_path):
    plan = build_test_plan(tmp_path)
    policy = TransformationPolicy([
        PolicyDecision("auth", "ALLOW", [], ["move_files"], []),
        PolicyDecision("users", "ALLOW", [], ["move_files"], [])
    ])
    registry = SkillRegistry()
    registry.register(Skill("reuse_extraction", "loc", "desc", ["move_files"], [], True, True))
    
    planner = GlobalWorkflowPlanner(str(tmp_path), policy, registry)
    gwf = planner.build(plan)
    
    engine = SimulationEngine(str(tmp_path))
    sim_res = engine.simulate_global(gwf, plan)
    
    assert sim_res.status == "READY"
    assert sim_res.files_affected == 2
    assert sim_res.change_size.files == 2
    assert sim_res.change_size.operations == 2
    assert sim_res.risk.level in ("LOW", "MEDIUM", "HIGH")
    assert sim_res.simulation_hash != ""

def test_simulation_determinism(tmp_path):
    plan = build_test_plan(tmp_path)
    policy = TransformationPolicy([
        PolicyDecision("auth", "ALLOW", [], ["move_files"], []),
        PolicyDecision("users", "ALLOW", [], ["move_files"], [])
    ])
    registry = SkillRegistry()
    registry.register(Skill("reuse_extraction", "loc", "desc", ["move_files"], [], True, True))
    
    planner = GlobalWorkflowPlanner(str(tmp_path), policy, registry)
    gwf = planner.build(plan)
    
    engine = SimulationEngine(str(tmp_path))
    sim_res1 = engine.simulate_global(gwf, plan)
    sim_res2 = engine.simulate_global(gwf, plan)
    
    assert sim_res1.simulation_hash == sim_res2.simulation_hash

def test_approval_binding_mismatch(tmp_path):
    plan = build_test_plan(tmp_path)
    policy = TransformationPolicy([
        PolicyDecision("auth", "ALLOW", [], ["move_files"], []),
        PolicyDecision("users", "ALLOW", [], ["move_files"], [])
    ])
    registry = SkillRegistry()
    registry.register(Skill("reuse_extraction", "loc", "desc", ["move_files"], [], True, True))
    
    planner = GlobalWorkflowPlanner(str(tmp_path), policy, registry)
    gwf = planner.build(plan)
    
    app_mgr = ApprovalLifecycleManager()
    approval = app_mgr.request_approval(plan.transaction_id, "GLOBAL", gwf.global_workflow_hash, "phash", "bhash", ["move_files"], simulation_hash="HASH_A")
    app_mgr.approve(approval.approval_id)
    
    orch = TransformationOrchestrator(tmp_path, plan, policy, registry, approvals={"auth": ["move_files"], "users": ["move_files"]})
    
    # Execute with WRONG simulation hash
    record = orch.execute_global_workflow(gwf, approval, app_mgr, mode="EXECUTE", simulation_hash="HASH_B")
    
    assert record.status == "REJECTED"
    assert "APPROVAL_MISMATCH" in record.errors[0]

def test_cross_candidate_conflict_simulation(tmp_path):
    plan = MultiCandidateTransformationPlan("tx_sim_conflict", target_root=str(tmp_path))
    c1 = CandidateTransformationPlan("auth", classification="REUSABLE", extraction_readiness="READY", recommendation="reuse")
    c1.actions.append(ExtractionAction("move_files", source="auth.py", destination="shared/conflict.py"))
    
    c2 = CandidateTransformationPlan("legacy", classification="REUSABLE", extraction_readiness="READY", recommendation="reuse")
    c2.actions.append(ExtractionAction("move_files", source="legacy.py", destination="shared/conflict.py"))
    
    plan.candidates = [c1, c2]
    
    policy = TransformationPolicy([
        PolicyDecision("auth", "ALLOW", [], ["move_files"], []),
        PolicyDecision("legacy", "ALLOW", [], ["move_files"], [])
    ])
    registry = SkillRegistry()
    registry.register(Skill("reuse_extraction", "loc", "desc", ["move_files"], [], True, True))
    
    planner = GlobalWorkflowPlanner(str(tmp_path), policy, registry)
    gwf = planner.build(plan)
    
    engine = SimulationEngine(str(tmp_path))
    sim_res = engine.simulate_global(gwf, plan)
    
    assert sim_res.status == "BLOCKED"
    assert "DESTINATION_CONFLICT" in sim_res.cross_candidate_conflicts[0]

def test_impact_comparisons():
    res1 = ImpactComparison.compare_planned_vs_simulated(["a.py"], ["a.py", "b.py"])
    assert res1 == "SIMULATION_EXPANDED_SCOPE"
    
    res2 = ImpactComparison.compare_simulated_vs_observed(["a.py"], ["a.py", "c.py"], ["a.py", "c.py"])
    assert res2 == "SIMULATION_UNDERESTIMATED"
    
    res3 = ImpactComparison.compare_simulated_vs_observed(["a.py"], ["a.py", "c.py"], ["a.py"])
    assert res3 == "UNEXPECTED"

from core.discovery.transformation import ExtractionAction
import pytest
from pathlib import Path

from core.skills.models import Skill, ExecutionResult
from core.skills.discovery import SkillDiscovery
from core.skills.registry import SkillRegistry
from core.execution.engine import ExecutionEngine
from core.discovery.transformation import TransformationPlan, MultiCandidateTransformationPlan, CandidateTransformationPlan, ExtractionBoundary
from core.discovery.transformation_policy import TransformationPolicy, PolicyDecision




def test_capability_matching():
    registry = SkillRegistry()
    registry.register(Skill("read_only", "loc", "desc", ["inspect_boundary", "run_tests"], [], False, True))
    registry.register(Skill("mutating_skill", "loc", "desc", ["move_files", "rewrite_imports"], [], True, True))
    
    match1 = registry.match_capabilities("auth", ["inspect_boundary"])
    assert match1.compatible is True
    assert match1.matching_skill == "read_only"
    
    match2 = registry.match_capabilities("auth", ["move_files", "create_adapter"])
    assert match2.compatible is False
    assert "create_adapter" in match2.missing_capabilities

def get_dummy_policy():
    plan = MultiCandidateTransformationPlan("tx_1", candidates=[
        CandidateTransformationPlan(
            candidate="auth",
            classification="REUSABLE",
            extraction_readiness="READY",
            recommendation="reuse",
            boundary=ExtractionBoundary(include=["modules/auth/service.py"], forbidden=["modules/db/config.py"])
        ),
        CandidateTransformationPlan(
            candidate="db",
            classification="HIGHLY_COUPLED",
            extraction_readiness="BLOCKED",
            recommendation="do_not_reuse"
        )
    ])
    policy = TransformationPolicy(decisions=[
        PolicyDecision(
            candidate="auth",
            decision="ALLOW_WITH_VALIDATION",
            allowed=["inspect_boundary"],
            approval_required=["move_files"],
            denied=["delete_source"]
        ),
        PolicyDecision(
            candidate="db",
            decision="DENY",
            allowed=[],
            approval_required=[],
            denied=["move_files", "inspect_boundary"]
        )
    ])
    return plan, policy







def test_execution_engine_rejects_missing_capability(tmp_path):
    plan, policy = get_dummy_policy()
    registry = SkillRegistry()
    # Read-only skill cannot move files
    registry.register(Skill("skill1", "loc", "desc", ["inspect_boundary"], [], False, True))
    
    engine = ExecutionEngine(tmp_path, plan, policy, registry, approvals={"auth": ["move_files"]})
    result = engine.execute("auth", [ExtractionAction("move_files", source="modules/auth/service.py", destination="shared/auth")], mode="EXECUTE")
    
    assert result.status == "REJECTED"

def test_execution_engine_rejects_path_traversal(tmp_path):
    plan, policy = get_dummy_policy()
    registry = SkillRegistry()
    registry.register(Skill("skill1", "loc", "desc", ["move_files"], [], True, True))
    
    (tmp_path / "modules" / "auth").mkdir(parents=True, exist_ok=True)
    (tmp_path / "modules" / "auth" / "service.py").write_text("code")
    engine = ExecutionEngine(tmp_path, plan, policy, registry, approvals={"auth": ["move_files"]})
    result = engine.execute("auth", [ExtractionAction("move_files", source="modules/auth/service.py", destination="../../../etc/passwd")])
    
    assert result.status == "ROLLED_BACK"
    assert result.status == "ROLLED_BACK"




def test_execution_engine_dry_run_success(tmp_path):
    plan, policy = get_dummy_policy()
    registry = SkillRegistry()
    registry.register(Skill("skill1", "loc", "desc", ["move_files"], [], True, True))
    
    (tmp_path / "modules" / "auth").mkdir(parents=True, exist_ok=True)
    (tmp_path / "modules" / "auth" / "service.py").write_text("code")
    
    engine = ExecutionEngine(tmp_path, plan, policy, registry, approvals={"auth": ["move_files"]})
    result = engine.execute("auth", [ExtractionAction("move_files", source="modules/auth/service.py", destination="shared/auth")], mode="DRY_RUN")
    
    assert result.status == "SUCCESS"
    # check that physical move did not happen
    assert (tmp_path / "modules" / "auth" / "service.py").exists()

def test_execution_engine_execute_success(tmp_path):
    plan, policy = get_dummy_policy()
    registry = SkillRegistry()
    registry.register(Skill("skill1", "loc", "desc", ["move_files"], [], True, True))
    
    (tmp_path / "modules" / "auth").mkdir(parents=True, exist_ok=True)
    (tmp_path / "modules" / "auth" / "service.py").write_text("code")
    
    engine = ExecutionEngine(tmp_path, plan, policy, registry, approvals={"auth": ["move_files"]})
    result = engine.execute("auth", [ExtractionAction("move_files", source="modules/auth/service.py", destination="shared/auth")], mode="EXECUTE")
    
    assert result.status == "COMMITTED"
    # Physical move happened













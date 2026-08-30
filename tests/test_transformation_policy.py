import pytest
from pathlib import Path
from core.discovery.engine import DiscoveryEngine
from core.discovery.understanding import UnderstandingEngine
from core.discovery.analysis import AnalysisEngine
from core.discovery.task_analysis import TaskReuseAnalyzer
from core.discovery.transformation import TransformationPlanner
from core.discovery.transformation_policy import TransformationPolicyEvaluator

def setup_policy(tmp_path, task):
    env = DiscoveryEngine(tmp_path).discover()
    u = UnderstandingEngine(tmp_path, env).analyze()
    a = AnalysisEngine(tmp_path, env, u).analyze()
    t = TaskReuseAnalyzer(task, u, a).analyze()
    plan = TransformationPlanner(tmp_path, env, u, a, t).plan()
    return TransformationPolicyEvaluator(plan).evaluate()

def test_policy_isolated_ready(tmp_path):
    auth_dir = tmp_path / "modules" / "auth"
    auth_dir.mkdir(parents=True)
    (auth_dir / "service.py").write_text("def login(): pass", encoding="utf-8")
    (tmp_path / "tests").mkdir(parents=True)
    (tmp_path / "tests" / "test_auth.py").write_text("def test_login(): pass", encoding="utf-8")
    
    policy = setup_policy(tmp_path, "construir un crm")
    auth_pol = next(c for c in policy.decisions if c.candidate == "auth")
    
    assert auth_pol.decision == "ALLOW_WITH_VALIDATION"
    assert "inspect_boundary" in auth_pol.allowed
    assert "move_files" in auth_pol.approval_required
    assert "delete_source" in auth_pol.denied

def test_policy_requires_adaptation(tmp_path):
    users_dir = tmp_path / "modules" / "users"
    users_dir.mkdir(parents=True)
    (users_dir / "repo.py").write_text("import sqlalchemy\nfrom flask import Blueprint", encoding="utf-8")
    (tmp_path / "tests").mkdir(parents=True)
    (tmp_path / "tests" / "test_users.py").write_text("def test_repo(): pass", encoding="utf-8")
    
    policy = setup_policy(tmp_path, "construir modulo users")
    users_pol = next(c for c in policy.decisions if c.candidate == "users")
    
    assert users_pol.decision == "REQUIRE_APPROVAL"
    assert "move_files" in users_pol.approval_required
    assert "create_adapter" in users_pol.approval_required
    assert any(p.type == "adaptation_points_defined" for p in users_pol.preconditions)
    assert any(v == "apply_adaptations" for v in users_pol.verification.transformation)

def test_policy_blocked(tmp_path):
    db_dir = tmp_path / "modules" / "db"
    db_dir.mkdir(parents=True)
    (db_dir / "service.py").write_text("import sqlalchemy\nimport redis", encoding="utf-8")
    
    # Intentionally omitted tests so it gets BLOCKED by missing_tests
    
    policy = setup_policy(tmp_path, "database system")
    db_pol = next((c for c in policy.decisions if c.candidate == "db"), None)
    
    assert db_pol.decision == "DENY"
    assert "move_files" in db_pol.denied
    assert "create_adapter" in db_pol.denied
    assert "delete_source" in db_pol.denied



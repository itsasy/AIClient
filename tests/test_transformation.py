import pytest
from pathlib import Path
import os
import json

from core.discovery.engine import DiscoveryEngine
from core.discovery.understanding import UnderstandingEngine
from core.discovery.analysis import AnalysisEngine
from core.discovery.task_analysis import TaskReuseAnalyzer
from core.discovery.transformation import TransformationPlanner

def setup_transformation(tmp_path, task):
    env = DiscoveryEngine(tmp_path).discover()
    u = UnderstandingEngine(tmp_path, env).analyze()
    a = AnalysisEngine(tmp_path, env, u).analyze()
    t = TaskReuseAnalyzer(task, u, a).analyze()
    return TransformationPlanner(tmp_path, env, u, a, t).plan()

def test_transformation_isolated_reusable(tmp_path):
    auth_dir = tmp_path / "modules" / "auth"
    auth_dir.mkdir(parents=True)
    (auth_dir / "service.py").write_text("def login(): pass", encoding="utf-8")
    (tmp_path / "tests").mkdir(parents=True)
    (tmp_path / "tests" / "test_auth.py").write_text("def test_login(): pass", encoding="utf-8")
    
    plan = setup_transformation(tmp_path, "construir un crm")
    auth_plan = next(c for c in plan.candidates if c.candidate == "auth")
    
    assert auth_plan.extraction_readiness == "READY"
    assert any('service.py' in b for b in auth_plan.boundary.include)

def test_transformation_requires_adaptation(tmp_path):
    users_dir = tmp_path / "modules" / "users"
    users_dir.mkdir(parents=True)
    (users_dir / "repo.py").write_text("import sqlalchemy\nfrom flask import Blueprint", encoding="utf-8")
    (tmp_path / "tests").mkdir(parents=True)
    (tmp_path / "tests" / "test_users.py").write_text("def test_repo(): pass", encoding="utf-8")
    
    plan = setup_transformation(tmp_path, "construir modulo users")
    users_plan = next(c for c in plan.candidates if c.candidate == "users")
    
    assert users_plan.extraction_readiness == "REQUIRES_ADAPTATION"
    assert any(a.type == "persistence_adapter" for a in users_plan.adaptation_points)
    assert any(a.type == "framework_adapter" for a in users_plan.adaptation_points)

def test_transformation_blocked_highly_coupled(tmp_path):
    db_dir = tmp_path / "modules" / "db"
    db_dir.mkdir(parents=True)
    (db_dir / "service.py").write_text("import sqlalchemy\nimport redis\nimport psycopg2\nimport fs\nimport a\nimport b\nimport c", encoding="utf-8")
    
    # Needs a, b, c to trigger internal coupling score
    (tmp_path / "modules" / "a").mkdir(parents=True)
    (tmp_path / "modules" / "b").mkdir(parents=True)
    (tmp_path / "modules" / "c").mkdir(parents=True)
    
    plan = setup_transformation(tmp_path, "database system")
    db_plan = next((c for c in plan.candidates if c.candidate == "db"), None)
    
    assert db_plan is not None
    assert db_plan.extraction_readiness == "BLOCKED"
    assert any(r.type == "infrastructure_leakage" for r in db_plan.risks)

def test_transformation_vertical_specific_blocked(tmp_path):
    clin_dir = tmp_path / "modules" / "odontogram"
    clin_dir.mkdir(parents=True)
    (clin_dir / "service.py").write_text("import odontogram", encoding="utf-8")
    
    plan = setup_transformation(tmp_path, "app de restaurante")
    clin_plan = next(c for c in plan.candidates if c.candidate == "odontogram")
    
    assert clin_plan.extraction_readiness == "BLOCKED"
    assert any(r.type == "vertical_domain_leakage" for r in clin_plan.risks)




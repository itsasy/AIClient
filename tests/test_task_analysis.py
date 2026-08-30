import pytest
from pathlib import Path
import os
import json

from core.discovery.engine import DiscoveryEngine
from core.discovery.understanding import UnderstandingEngine
from core.discovery.analysis import AnalysisEngine
from core.discovery.task_analysis import TaskReuseAnalyzer

def setup_analysis(tmp_path, task):
    env = DiscoveryEngine(tmp_path).discover()
    u = UnderstandingEngine(tmp_path, env).analyze()
    a = AnalysisEngine(tmp_path, env, u).analyze()
    t = TaskReuseAnalyzer(task, u, a).analyze()
    return t

def test_task_analysis_reusable_relevant(tmp_path):
    auth_dir = tmp_path / "modules" / "auth"
    auth_dir.mkdir(parents=True)
    (auth_dir / "service.py").write_text("def login(): pass", encoding="utf-8")
    
    t = setup_analysis(tmp_path, "construir un sistema de auth")
    rec = next(c for c in t.relevant_candidates if c.module == "auth")
    
    assert rec.relevance == "high"
    assert rec.recommendation == "reuse"
    assert rec.classification == "REUSABLE"

def test_task_analysis_reusable_with_adaptation_relevant(tmp_path):
    users_dir = tmp_path / "modules" / "users"
    users_dir.mkdir(parents=True)
    (users_dir / "routes.py").write_text("from flask import Blueprint\nimport sqlalchemy", encoding="utf-8")
    
    t = setup_analysis(tmp_path, "sistema de users")
    rec = next(c for c in t.relevant_candidates if c.module == "users")
    
    assert rec.relevance == "high"
    assert rec.recommendation == "reuse_with_adaptation"
    assert "Framework adapters for: flask" in rec.adaptation_points
    assert "Infrastructure adapters for: sqlalchemy" in rec.adaptation_points

def test_task_analysis_vertical_specific_not_relevant(tmp_path):
    clin_dir = tmp_path / "modules" / "clinical"
    clin_dir.mkdir(parents=True)
    (clin_dir / "service.py").write_text("import patients", encoding="utf-8")
    
    t = setup_analysis(tmp_path, "construir una app de restaurante")
    rec = next(c for c in t.irrelevant_candidates if c.module == "clinical")
    
    assert rec.recommendation == "do_not_reuse"
    assert rec.classification == "VERTICAL_SPECIFIC"

def test_task_analysis_highly_coupled(tmp_path):
    db_dir = tmp_path / "modules" / "db"
    db_dir.mkdir(parents=True)
    # Simulate high coupling
    content = "import a\nimport b\nimport c\nimport sqlalchemy\nimport redis\nimport psycopg2\nimport fs"
    (db_dir / "service.py").write_text(content, encoding="utf-8")
    
    # We also need a, b, c to be recognized as internal modules so it gets a high score
    (tmp_path / "modules" / "a").mkdir(parents=True)
    (tmp_path / "modules" / "b").mkdir(parents=True)
    (tmp_path / "modules" / "c").mkdir(parents=True)
    
    t = setup_analysis(tmp_path, "construir db")
    rec = next(c for c in t.relevant_candidates if c.module == "db")
    
    assert rec.classification == "HIGHLY_COUPLED"
    assert rec.recommendation == "reuse_as_reference"

def test_task_analysis_reusable_irrelevant(tmp_path):
    reports_dir = tmp_path / "modules" / "reports"
    reports_dir.mkdir(parents=True)
    (reports_dir / "service.py").write_text("def gen(): pass", encoding="utf-8")
    
    t = setup_analysis(tmp_path, "auth system")
    rec = next((c for c in t.irrelevant_candidates if c.module == "reports"), None)
    
    assert rec is not None
    assert rec.classification == "REUSABLE"
    assert rec.recommendation == "do_not_reuse"

def test_task_analysis_empty_task(tmp_path):
    auth_dir = tmp_path / "modules" / "auth"
    auth_dir.mkdir(parents=True)
    
    t = setup_analysis(tmp_path, "")
    assert t.confidence == "low"
    assert "No task provided" in t.summary


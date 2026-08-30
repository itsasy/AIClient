import pytest
from pathlib import Path
import os
import json

from core.discovery.engine import DiscoveryEngine
from core.discovery.understanding import UnderstandingEngine
from core.discovery.analysis import AnalysisEngine

def setup_analysis(tmp_path):
    env = DiscoveryEngine(tmp_path).discover()
    u = UnderstandingEngine(tmp_path, env).analyze()
    a = AnalysisEngine(tmp_path, env, u).analyze()
    return u, a

def test_analysis_case_1_isolated_module(tmp_path):
    auth_dir = tmp_path / "modules" / "auth"
    auth_dir.mkdir(parents=True)
    (auth_dir / "service.py").write_text("def login(): pass", encoding="utf-8")
    (auth_dir / "__init__.py").touch()
    
    u, a = setup_analysis(tmp_path)
    auth_reuse = next(r for r in a.reuse_analysis if r.module == "auth")
    assert auth_reuse.classification == "REUSABLE"

def test_analysis_case_2_framework_coupling(tmp_path):
    auth_dir = tmp_path / "modules" / "auth"
    auth_dir.mkdir(parents=True)
    (auth_dir / "routes.py").write_text("from flask import Blueprint", encoding="utf-8")
    
    u, a = setup_analysis(tmp_path)
    auth_boundary = next(b for b in a.boundaries if b.name == "auth")
    assert "flask" in auth_boundary.framework_dependencies
    
    auth_reuse = next(r for r in a.reuse_analysis if r.module == "auth")
    assert auth_reuse.classification == "REUSABLE_WITH_ADAPTATION"
    assert any("Framework adapters" in point for point in auth_reuse.adaptation_points)

def test_analysis_case_3_infrastructure_coupling(tmp_path):
    cat_dir = tmp_path / "modules" / "catalog"
    cat_dir.mkdir(parents=True)
    (cat_dir / "repo.py").write_text("import sqlalchemy", encoding="utf-8")
    
    u, a = setup_analysis(tmp_path)
    cat_boundary = next(b for b in a.boundaries if b.name == "catalog")
    assert "sqlalchemy" in cat_boundary.infrastructure_dependencies
    
    cat_reuse = next(r for r in a.reuse_analysis if r.module == "catalog")
    assert cat_reuse.classification == "REUSABLE_WITH_ADAPTATION"

def test_analysis_case_4_internal_coupling(tmp_path):
    auth_dir = tmp_path / "modules" / "auth"
    auth_dir.mkdir(parents=True)
    users_dir = tmp_path / "modules" / "users"
    users_dir.mkdir(parents=True)
    
    (auth_dir / "service.py").write_text("from users import User", encoding="utf-8")
    (users_dir / "model.py").write_text("class User: pass", encoding="utf-8")
    
    u, a = setup_analysis(tmp_path)
    auth_boundary = next(b for b in a.boundaries if b.name == "auth")
    assert "users" in auth_boundary.internal_dependencies

def test_analysis_case_5_circular_dependency(tmp_path):
    a_dir = tmp_path / "modules" / "a"
    a_dir.mkdir(parents=True)
    b_dir = tmp_path / "modules" / "b"
    b_dir.mkdir(parents=True)
    
    (a_dir / "service.py").write_text("import b", encoding="utf-8")
    (b_dir / "service.py").write_text("import a", encoding="utf-8")
    
    u, a = setup_analysis(tmp_path)
    circ_bottleneck = next((b for b in a.new_bottlenecks if b.type == "circular_dependency"), None)
    assert circ_bottleneck is not None

def test_analysis_case_6_vertical_specific(tmp_path):
    clin_dir = tmp_path / "modules" / "clinical"
    clin_dir.mkdir(parents=True)
    (clin_dir / "service.py").write_text("import patients", encoding="utf-8")
    
    u, a = setup_analysis(tmp_path)
    clin_reuse = next(r for r in a.reuse_analysis if r.module == "clinical")
    assert clin_reuse.classification == "VERTICAL_SPECIFIC"

def test_analysis_case_7_unknown(tmp_path):
    u, a = setup_analysis(tmp_path)
    assert len(a.reuse_analysis) == 0

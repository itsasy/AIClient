import pytest
from pathlib import Path
import os

from core.discovery.engine import DiscoveryEngine
from core.discovery.understanding import UnderstandingEngine

def test_understanding_python_flask(tmp_path):
    (tmp_path / "app.py").touch()
    (tmp_path / "config.py").touch()
    (tmp_path / "requirements.txt").write_text("Flask", encoding="utf-8")
    api_dir = tmp_path / "api"
    api_dir.mkdir()
    (api_dir / "routes.py").touch()
    
    env = DiscoveryEngine(tmp_path).discover()
    u = UnderstandingEngine(tmp_path, env).analyze()
    
    assert any(e["path"] == "app.py" for e in u.entrypoints)
    assert any(c["path"] == "config.py" for c in u.configuration)
    assert any("api" in a["path"] for a in u.api_surface)
    assert u.architecture == "Backend / API-heavy"

def test_understanding_node(tmp_path):
    (tmp_path / "package.json").touch()
    (tmp_path / "index.js").touch()
    components = tmp_path / "components"
    components.mkdir()
    (components / "App.js").touch()
    
    env = DiscoveryEngine(tmp_path).discover()
    u = UnderstandingEngine(tmp_path, env).analyze()
    
    assert any("index.js" in e["path"] for e in u.entrypoints)
    assert any("components" in f["path"] for f in u.frontend_surface)
    assert u.architecture == "Frontend-heavy"

def test_understanding_laravel(tmp_path):
    (tmp_path / "artisan").touch()
    (tmp_path / "composer.json").touch()
    app_dir = tmp_path / "app" / "Models"
    app_dir.mkdir(parents=True)
    routes = tmp_path / "routes"
    routes.mkdir()
    
    env = DiscoveryEngine(tmp_path).discover()
    u = UnderstandingEngine(tmp_path, env).analyze()
    
    assert any(e["path"] == "artisan" for e in u.entrypoints)
    assert any("routes" in a["path"] for a in u.api_surface)
    assert any(m["name"] == "Models" for m in u.modules)

def test_understanding_android(tmp_path):
    (tmp_path / "build.gradle").touch()
    manifest_dir = tmp_path / "app" / "src" / "main"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "AndroidManifest.xml").touch()
    
    env = DiscoveryEngine(tmp_path).discover()
    u = UnderstandingEngine(tmp_path, env).analyze()
    
    assert any("AndroidManifest.xml" in e["path"] for e in u.entrypoints)

def test_understanding_vanilla_js(tmp_path):
    ui_dir = tmp_path / "ui" / "pos_shell" / "js" / "views"
    ui_dir.mkdir(parents=True)
    
    env = DiscoveryEngine(tmp_path).discover()
    u = UnderstandingEngine(tmp_path, env).analyze()
    
    assert any("ui" in f["path"] for f in u.frontend_surface)

def test_understanding_bottlenecks_missing_tests(tmp_path):
    mod_dir = tmp_path / "modules" / "auth"
    mod_dir.mkdir(parents=True)
    
    env = DiscoveryEngine(tmp_path).discover()
    u = UnderstandingEngine(tmp_path, env).analyze()
    
    # Auth module has no global tests or inside test
    bottleneck = next((b for b in u.bottlenecks if b.type == "missing_tests"), None)
    assert bottleneck is not None
    assert bottleneck.severity == "high"

def test_understanding_sensitive_files(tmp_path):
    (tmp_path / ".env").touch()
    (tmp_path / "aws_credentials.pem").touch()
    
    env = DiscoveryEngine(tmp_path).discover()
    u = UnderstandingEngine(tmp_path, env).analyze()
    
    secrets = [c for c in u.configuration if c.get("type") == "secret-bearing-file"]
    assert len(secrets) == 2

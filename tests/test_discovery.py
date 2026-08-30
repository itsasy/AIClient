import pytest
from pathlib import Path
import tempfile
import os

from core.discovery.engine import DiscoveryEngine
from core.discovery.environment import ProjectEnvironment

def test_discovery_python_pytest(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.pytest.ini_options]\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    
    engine = DiscoveryEngine(tmp_path)
    env = engine.discover()
    
    assert "Python" in env.languages
    assert any(runner.value == "pytest" for runner in env.test_runner)
    assert any("pytest" in cmd.value for cmd in env.commands["test"])

def test_discovery_node(tmp_path):
    (tmp_path / "package.json").write_text('{"scripts": {"test": "jest", "build": "vite build"}}', encoding="utf-8")
    
    engine = DiscoveryEngine(tmp_path)
    env = engine.discover()
    
    assert "JavaScript" in env.languages
    assert any(runner.value == "npm scripts" for runner in env.test_runner)
    assert any("npm test" in cmd.value for cmd in env.commands["test"])
    assert any("npm run build" in cmd.value for cmd in env.commands["build"])

def test_discovery_laravel(tmp_path):
    (tmp_path / "composer.json").touch()
    (tmp_path / "artisan").touch()
    (tmp_path / "phpunit.xml").touch()
    (tmp_path / "routes").mkdir()
    (tmp_path / "app").mkdir()
    
    engine = DiscoveryEngine(tmp_path)
    env = engine.discover()
    
    assert "PHP" in env.languages
    assert "Laravel" in env.frameworks
    assert any(runner.value == "PHPUnit/Pest" for runner in env.test_runner)
    assert any("php artisan test" in cmd.value for cmd in env.commands["test"])
    roles = [d["role"] for d in env.important_directories]
    assert "routes" in roles
    assert "application" in roles

def test_discovery_android(tmp_path):
    (tmp_path / "settings.gradle").touch()
    (tmp_path / "build.gradle").touch()
    app_dir = tmp_path / "app" / "src" / "main"
    app_dir.mkdir(parents=True)
    (app_dir / "AndroidManifest.xml").touch()
    
    engine = DiscoveryEngine(tmp_path)
    env = engine.discover()
    
    assert "Java/Kotlin" in env.languages
    assert "Android" in env.frameworks
    assert any("gradlew" in cmd.value for cmd in env.commands["test"])

def test_discovery_unknown(tmp_path):
    engine = DiscoveryEngine(tmp_path)
    env = engine.discover()
    
    assert len(env.languages) == 0
    assert len(env.frameworks) == 0
    assert not env.test_runner

def test_discovery_multi_tech(tmp_path):
    (tmp_path / "package.json").write_text('{}', encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text('', encoding="utf-8")
    
    engine = DiscoveryEngine(tmp_path)
    env = engine.discover()
    
    assert "JavaScript" in env.languages
    assert "Python" in env.languages

def test_discovery_python_no_test_runner(tmp_path):
    # Only requirements.txt exists
    (tmp_path / "requirements.txt").write_text("Flask", encoding="utf-8")
    
    engine = DiscoveryEngine(tmp_path)
    env = engine.discover()
    
    assert "Python" in env.languages
    assert not env.test_runner
    assert len(env.commands["test"]) == 0
    
def test_test_workflow_no_command(tmp_path):
    from core.workflows.test import TestWorkflow
    from core.config import Config
    
    # Empty dir
    root = tmp_path
    
    # Monkeypatch Config root
    Config.TARGET_PROJECT_ROOT = root
    
    workflow = TestWorkflow()
    plan = workflow.execute("product")
    
    assert plan.status == "not_available"
    assert "No test command could be determined" in plan.error

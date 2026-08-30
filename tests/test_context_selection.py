import pytest
import json
from dataclasses import dataclass, field
from core.discovery.context_selection import ContextSelector

@dataclass
class DummyPlan:
    metadata: dict = field(default_factory=dict)
    objective: str = "Construir CRM clinica"
    original_task: str = ""

def test_context_selector_small_project():
    plan = DummyPlan(metadata={"workflow": "spec"})
    knowledge = {
        "environment": {"languages": ["python"]},
        "understanding": {"architecture": "API"},
        "task_analysis": {
            "relevant_candidates": [
                {
                    "module": "auth",
                    "recommendation": "reuse",
                    "relevance": "high",
                    "evidence": ["auth/"]
                }
            ],
            "irrelevant_candidates": [],
            "risks": []
        }
    }
    
    selector = ContextSelector(plan=plan, budget=12000)
    ctx = selector.select(knowledge)
    
    assert ctx["context_mode"] == "focused"
    assert "omitted" not in ctx
    assert len(ctx["relevant_candidates"]) == 1
    assert ctx["relevant_candidates"][0]["name"] == "auth"
    assert "evidence" in ctx["relevant_candidates"][0]

def test_context_selector_large_project_omits_irrelevant():
    plan = DummyPlan(metadata={"workflow": "plan"})
    knowledge = {
        "environment": {"languages": ["python"]},
        "understanding": {"architecture": "Fullstack"},
        "task_analysis": {
            "relevant_candidates": [
                {
                    "module": "auth",
                    "recommendation": "reuse",
                    "relevance": "high"
                }
            ],
            "irrelevant_candidates": [
                {"module": f"mod_{i}"} for i in range(50)
            ],
            "risks": ["Global risk"]
        }
    }
    
    selector = ContextSelector(plan=plan, budget=12000)
    ctx = selector.select(knowledge)
    
    assert ctx["omitted"]["module_count"] == 50
    assert len(ctx["relevant_candidates"]) == 1

def test_context_selector_budget_degradation():
    plan = DummyPlan(metadata={"workflow": "spec"})
    # create a huge evidence list to trigger budget degradation
    large_evidence = [f"file_{i}.py" for i in range(1000)]
    
    knowledge = {
        "environment": {"languages": ["python"]},
        "understanding": {"architecture": "API"},
        "task_analysis": {
            "relevant_candidates": [
                {
                    "module": "auth",
                    "recommendation": "reuse",
                    "relevance": "high",
                    "evidence": large_evidence,
                    "adaptation_points": ["some adapter"]
                }
            ]
        }
    }
    
    # Restrict budget so it has to drop evidence
    selector = ContextSelector(plan=plan, budget=1000)
    ctx = selector.select(knowledge)
    
    assert ctx["relevant_candidates"][0]["evidence"] == ["evidence omitted due to budget"]
    
def test_context_selector_test_phase():
    plan = DummyPlan(metadata={"workflow": "test"})
    knowledge = {
        "environment": {"test_runner": "pytest"},
        "understanding": {"test_surface": ["tests/test_auth.py"]},
        "task_analysis": {}
    }
    
    selector = ContextSelector(plan=plan, budget=12000)
    ctx = selector.select(knowledge)
    
    assert ctx["test_runner"] == "pytest"
    assert "tests/test_auth.py" in ctx["test_surface"]

def test_unknown_remains_unknown():
    plan = DummyPlan(metadata={"workflow": "spec"})
    knowledge = {
        "environment": {}, # missing test runner
        "understanding": {}
    }
    
    selector = ContextSelector(plan=plan)
    ctx = selector.select(knowledge)
    assert ctx["project"]["test_runner"] == "unknown"

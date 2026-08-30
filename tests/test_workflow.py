import pytest
from pathlib import Path
import time
from core.discovery.transformation import TransformationPlan, MultiCandidateTransformationPlan, CandidateTransformationPlan, ExtractionBoundary, ExtractionAction
from core.discovery.transformation_policy import TransformationPolicy, PolicyDecision
from core.skills.registry import SkillRegistry
from core.skills.models import Skill
from core.execution.workflow import ExtractionWorkflowPlanner, WorkflowStep, WorkflowGraph
from core.execution.approval_preview import ApprovalPreviewGenerator, ApprovalRecord

def get_dummy_plan():
    plan = MultiCandidateTransformationPlan("tx_1", candidates=[
        CandidateTransformationPlan(
            candidate="clinical",
            classification="REUSABLE",
            extraction_readiness="READY",
            recommendation="reuse",
            boundary=ExtractionBoundary(include=["modules/clinical/service.py"]),
            adaptation_requirements=["persistence_adapter"],
            actions=[
                ExtractionAction("create_declared_adapter", destination="shared/clinical/adapter.py"),
                ExtractionAction("rewrite_imports", source="modules/clinical/service.py", target="foo", destination="bar"),
                ExtractionAction("move_files", source="modules/clinical/service.py", destination="shared/clinical/service.py")
            ]
        )
    ])
    policy = TransformationPolicy(decisions=[
        PolicyDecision(
            candidate="clinical",
            decision="ALLOW_WITH_VALIDATION",
            allowed=[],
            approval_required=["move_files", "rewrite_imports", "create_declared_adapter"],
            denied=[]
        )
    ])
    registry = SkillRegistry()
    registry.register(Skill("skill1", "loc", "desc", ["move_files", "rewrite_imports", "create_declared_adapter"], [], True, True))
    return plan, policy, registry

def test_workflow_dependency_ordering():
    plan, policy, registry = get_dummy_plan()
    planner = ExtractionWorkflowPlanner("/tmp/mock", policy, registry)
    workflow = planner.build(plan.candidates[0])
    
    assert workflow.status == "READY"
    ordered = workflow.graph.get_ordered_steps()
    assert len(ordered) == 3
    
    # Ordering must be: adapter -> rewrite -> move
    assert ordered[0].operation == "create_declared_adapter"
    assert ordered[1].operation == "rewrite_imports"
    assert ordered[2].operation == "move_files"

def test_workflow_dependency_cycle():
    graph = WorkflowGraph()
    graph.add_step(WorkflowStep("1", "op1", "cand", dependencies=["2"]))
    graph.add_step(WorkflowStep("2", "op2", "cand", dependencies=["1"]))
    
    with pytest.raises(ValueError) as exc:
        graph.get_ordered_steps()
    assert "dependency_cycle" in str(exc.value)

def test_workflow_preview_generation():
    plan, policy, registry = get_dummy_plan()
    planner = ExtractionWorkflowPlanner("/tmp/mock", policy, registry)
    workflow = planner.build(plan.candidates[0])
    
    preview_gen = ApprovalPreviewGenerator(policy)
    preview = preview_gen.generate_preview(workflow)
    
    assert preview["candidate"] == "clinical"
    assert preview["files_to_move"] == 1
    assert preview["files_to_create"] == 1
    assert preview["files_to_modify"] == 1
    assert "move_files" in preview["approval_required"]
    assert "shared/clinical/adapter.py" in preview["adapters"]

def test_workflow_hash_integrity():
    plan, policy, registry = get_dummy_plan()
    planner = ExtractionWorkflowPlanner("/tmp/mock", policy, registry)
    
    workflow_1 = planner.build(plan.candidates[0])
    hash_1 = workflow_1.workflow_hash
    
    # Modify the plan slightly
    plan.candidates[0].boundary.include.append("modules/clinical/extra.py")
    workflow_2 = planner.build(plan.candidates[0])
    hash_2 = workflow_2.workflow_hash
    
    assert hash_1 != hash_2



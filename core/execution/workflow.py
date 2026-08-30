import hashlib
import json
import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

from core.discovery.transformation import CandidateTransformationPlan, ExtractionAction
from core.discovery.transformation_policy import TransformationPolicy
from core.skills.registry import SkillRegistry

@dataclass
class ExtractionScope:
    candidate: str
    source_root: str
    destination_root: str
    included_files: List[str] = field(default_factory=list)
    forbidden_files: List[str] = field(default_factory=list)
    declared_adaptations: List[str] = field(default_factory=list)

@dataclass
class WorkflowStep:
    step_id: str
    operation: str
    candidate: str
    inputs: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    required_capabilities: List[str] = field(default_factory=list)
    required_approval: bool = False
    status: str = "PENDING"  # PENDING, READY, BLOCKED, EXECUTING, COMPLETED, FAILED, SKIPPED

@dataclass
class WorkflowGraph:
    nodes: Dict[str, WorkflowStep] = field(default_factory=dict)
    edges: Dict[str, List[str]] = field(default_factory=dict)  # step_id -> depends_on (step_ids)
    
    def add_step(self, step: WorkflowStep):
        self.nodes[step.step_id] = step
        self.edges[step.step_id] = step.dependencies

    def get_ordered_steps(self) -> List[WorkflowStep]:
        # Topological sort
        visited = set()
        temp_mark = set()
        order = []
        
        def visit(n: str):
            if n in temp_mark:
                raise ValueError("WORKFLOW_BLOCKED: dependency_cycle")
            if n not in visited:
                temp_mark.add(n)
                for dep in self.edges.get(n, []):
                    visit(dep)
                temp_mark.remove(n)
                visited.add(n)
                order.append(self.nodes[n])
                
        for node in self.nodes.keys():
            if node not in visited:
                visit(node)
                
        return order

@dataclass
class ExtractionWorkflow:
    workflow_id: str
    candidate: str
    scope: ExtractionScope
    graph: WorkflowGraph
    status: str = "PENDING"
    reason: str = ""
    workflow_hash: str = ""
    
    def generate_hash(self):
        steps_data = []
        for step in self.graph.get_ordered_steps():
            steps_data.append({
                "operation": step.operation,
                "inputs": step.inputs,
                "dependencies": step.dependencies
            })
        
        payload = {
            "candidate": self.candidate,
            "scope_include": sorted(self.scope.included_files),
            "steps": steps_data
        }
        self.workflow_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

class ExtractionWorkflowPlanner:
    def __init__(self, target_root: str, policy: TransformationPolicy, registry: SkillRegistry):
        self.target_root = target_root
        self.policy = policy
        self.registry = registry

    def build(self, plan: CandidateTransformationPlan) -> ExtractionWorkflow:
        workflow_id = str(uuid.uuid4())
        scope = ExtractionScope(
            candidate=plan.candidate,
            source_root=self.target_root,
            destination_root=self.target_root,
            included_files=plan.boundary.include.copy(),
            forbidden_files=plan.boundary.forbidden.copy(),
            declared_adaptations=plan.adaptation_requirements.copy()
        )
        
        graph = WorkflowGraph()
        workflow = ExtractionWorkflow(workflow_id, plan.candidate, scope, graph)
        
        cand_policy = next((p for p in self.policy.decisions if p.candidate == plan.candidate), None)
        if not cand_policy or cand_policy.decision == "DENY":
            workflow.status = "BLOCKED"
            workflow.reason = "policy_deny"
            return workflow
            
        if plan.extraction_readiness == "BLOCKED":
            workflow.status = "BLOCKED"
            workflow.reason = "candidate_blocked"
            return workflow
            
        # Check adapters logic
        declared_adapter_ops = [a for a in plan.actions if a.operation == "create_declared_adapter"]
        if plan.adaptation_requirements and not declared_adapter_ops:
            workflow.status = "BLOCKED"
            workflow.reason = "missing_declared_adaptation"
            return workflow
            
        if declared_adapter_ops and not plan.adaptation_requirements:
            workflow.status = "BLOCKED"
            workflow.reason = "ADAPTATION_UNSUPPORTED"
            return workflow

        # Map actions to steps with strict ordering
        # Order: 1) create_adapter 2) rewrite_imports 3) move_files
        step_ids = {}
        for action in plan.actions:
            step_id = str(uuid.uuid4())
            step_ids[action.operation] = step_id
            
        for action in plan.actions:
            deps = []
            if action.operation == "rewrite_declared_imports" or action.operation == "rewrite_imports":
                if "create_declared_adapter" in step_ids:
                    deps.append(step_ids["create_declared_adapter"])
            elif action.operation in ("move_files", "copy_files"):
                if "rewrite_declared_imports" in step_ids:
                    deps.append(step_ids["rewrite_declared_imports"])
                elif "rewrite_imports" in step_ids:
                    deps.append(step_ids["rewrite_imports"])
                if "create_declared_adapter" in step_ids:
                    deps.append(step_ids["create_declared_adapter"])

            step = WorkflowStep(
                step_id=step_ids[action.operation],
                operation=action.operation,
                candidate=plan.candidate,
                inputs={"source": action.source, "destination": action.destination, "target": action.target},
                dependencies=deps,
                required_capabilities=[action.operation],
                required_approval=(action.operation in cand_policy.approval_required)
            )
            
            # Verify capability
            match = self.registry.match_capabilities(plan.candidate, [action.operation])
            if not match.compatible:
                workflow.status = "BLOCKED"
                workflow.reason = f"missing_capability_{action.operation}"
                return workflow
                
            graph.add_step(step)

        try:
            workflow.generate_hash()
            workflow.status = "READY"
        except ValueError as e:
            workflow.status = "BLOCKED"
            workflow.reason = str(e)

        return workflow

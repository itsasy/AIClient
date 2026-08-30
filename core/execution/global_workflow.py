import hashlib
import json
import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

from core.discovery.transformation import MultiCandidateTransformationPlan, CandidateTransformationPlan
from core.discovery.transformation_policy import TransformationPolicy
from core.skills.registry import SkillRegistry
from core.execution.workflow import ExtractionWorkflow, ExtractionWorkflowPlanner

@dataclass
class GlobalWorkflow:
    global_workflow_id: str
    transaction_id: str
    candidate_workflows: Dict[str, ExtractionWorkflow] = field(default_factory=dict)
    global_workflow_hash: str = ""
    status: str = "PENDING"
    reason: str = ""
    
    def generate_global_hash(self):
        hashes = sorted([wf.workflow_hash for wf in self.candidate_workflows.values()])
        self.global_workflow_hash = hashlib.sha256("".join(hashes).encode()).hexdigest()
        
    def get_ordered_candidates(self, plan: MultiCandidateTransformationPlan) -> List[str]:
        plan.validate_dependencies()
        visited = set()
        order = []
        def visit(n):
            if n not in visited:
                cand = next(c for c in plan.candidates if c.candidate == n)
                for dep in cand.dependencies:
                    visit(dep)
                visited.add(n)
                order.append(n)
                
        for cand in plan.candidates:
            if cand.candidate not in visited:
                visit(cand.candidate)
        return order

class GlobalWorkflowPlanner:
    def __init__(self, target_root: str, policy: TransformationPolicy, registry: SkillRegistry):
        self.target_root = target_root
        self.policy = policy
        self.registry = registry
        self.individual_planner = ExtractionWorkflowPlanner(target_root, policy, registry)

    def build(self, plan: MultiCandidateTransformationPlan) -> GlobalWorkflow:
        gwf = GlobalWorkflow(str(uuid.uuid4()), plan.transaction_id)
        
        try:
            plan.validate_dependencies()
        except ValueError as e:
            gwf.status = "BLOCKED"
            gwf.reason = str(e)
            return gwf
            
        for cand in plan.candidates:
            # P17 Global boundary check (simulated)
            for file in cand.boundary.include:
                if file not in plan.global_boundary.include:
                    gwf.status = "BLOCKED"
                    gwf.reason = "BOUNDARY_CONFLICT"
                    return gwf

            cwf = self.individual_planner.build(cand)
            if cwf.status == "BLOCKED":
                gwf.status = "BLOCKED"
                gwf.reason = f"Candidate {cand.candidate} blocked: {cwf.reason}"
                return gwf
                
            gwf.candidate_workflows[cand.candidate] = cwf
            
        # Cross candidate conflicts checking (simple destination conflict detection)
        destinations = set()
        for cand_name, cwf in gwf.candidate_workflows.items():
            for step in cwf.graph.get_ordered_steps():
                dst = step.inputs.get("destination")
                if dst:
                    if dst in destinations:
                        gwf.status = "BLOCKED"
                        gwf.reason = "DESTINATION_CONFLICT"
                        return gwf
                    destinations.add(dst)
        
        gwf.generate_global_hash()
        gwf.status = "READY"
        return gwf

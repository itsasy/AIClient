import hashlib
import json
import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from pathlib import Path

from core.execution.workflow import ExtractionWorkflow
from core.execution.global_workflow import GlobalWorkflow
from core.discovery.transformation import MultiCandidateTransformationPlan
from core.execution.risk import RiskCalculator, RiskAnalysis

@dataclass
class ChangeSize:
    files: int = 0
    operations: int = 0

@dataclass
class SimulationResult:
    simulation_id: str
    status: str
    workflow_hash: str
    global_workflow_hash: str
    policy_hash: str
    boundary_hash: str
    
    files_affected: int = 0
    files_created: int = 0
    files_modified: int = 0
    files_moved: int = 0
    files_deleted: int = 0
    files_unchanged: int = 0
    
    imports_affected: int = 0
    adapters_required: int = 0
    dependencies_affected: int = 0
    
    cross_candidate_conflicts: List[str] = field(default_factory=list)
    risk: RiskAnalysis = field(default_factory=lambda: RiskAnalysis("UNKNOWN", 0, []))
    change_size: ChangeSize = field(default_factory=ChangeSize)
    
    expected_verification: Dict[str, str] = field(default_factory=dict)
    skill_selection_hash: str = ""
    specification_hash: str = ""
    graph_hash: str = ""
    
    per_candidate_impact: Dict[str, Any] = field(default_factory=dict)
    
    simulation_hash: str = ""
    
    def generate_hash(self):
        payload = {
            "workflow_hash": self.workflow_hash,
            "global_workflow_hash": self.global_workflow_hash,
            "policy_hash": self.policy_hash,
            "boundary_hash": self.boundary_hash,
            "files_affected": self.files_affected,
            "imports_affected": self.imports_affected,
            "adapters_required": self.adapters_required,
            "risk_score": self.risk.score,
            "skill_selection_hash": self.skill_selection_hash,
            "specification_hash": self.specification_hash,
            "graph_hash": self.graph_hash,
            "cross_candidate_conflicts": sorted(self.cross_candidate_conflicts)
        }
        self.simulation_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

class SimulationEngine:
    def __init__(self, target_root: str):
        self.target_root = Path(target_root)
        self.risk_calc = RiskCalculator()
        
    def simulate_global(self, gwf: GlobalWorkflow, plan: MultiCandidateTransformationPlan, skill_selection: dict = None) -> SimulationResult:
        res = SimulationResult(
            simulation_id=str(uuid.uuid4()),
            status="READY",
            workflow_hash="",
            global_workflow_hash=gwf.global_workflow_hash,
            policy_hash="N/A",  # simplified
            boundary_hash="N/A"
        )
        
        if gwf.status == "BLOCKED":
            res.status = "BLOCKED"
            if "DESTINATION_CONFLICT" in gwf.reason:
                res.cross_candidate_conflicts.append(gwf.reason)
            return res
            
        all_dests = set()
        operations_count = 0
        has_unknowns = False
        
        for cand_name, cwf in gwf.candidate_workflows.items():
            cand = next((c for c in plan.candidates if c.candidate == cand_name), None)
            
            c_files_affected = 0
            c_adapters = 0
            
            for step in cwf.graph.get_ordered_steps():
                operations_count += 1
                dst = step.inputs.get("destination")
                src = step.inputs.get("source")
                
                if step.operation in ("move_files", "copy_files"):
                    c_files_affected += 1
                    res.files_moved += 1 if step.operation == "move_files" else 0
                    if dst:
                        if dst in all_dests:
                            res.cross_candidate_conflicts.append(f"Conflict on {dst}")
                        all_dests.add(dst)
                elif step.operation in ("rewrite_declared_imports", "rewrite_imports"):
                    c_files_affected += 1
                    res.imports_affected += 1
                    res.files_modified += 1
                elif step.operation == "create_declared_adapter":
                    c_files_affected += 1
                    c_adapters += 1
                    res.files_created += 1
                    if dst:
                        all_dests.add(dst)
                        
            res.files_affected += c_files_affected
            res.adapters_required += c_adapters
            
            res.per_candidate_impact[cand_name] = {
                "files_affected": c_files_affected,
                "adapters_required": c_adapters
            }
            
        res.change_size = ChangeSize(files=res.files_affected, operations=operations_count)
        
        if res.cross_candidate_conflicts:
            res.status = "BLOCKED"
            
        res.risk = self.risk_calc.calculate(
            files_affected=res.files_affected,
            operations_count=operations_count,
            candidates_count=len(gwf.candidate_workflows),
            imports_affected=res.imports_affected,
            adapters_required=res.adapters_required,
            has_conflicts=len(res.cross_candidate_conflicts) > 0,
            has_unknowns=has_unknowns
        )
        
        if skill_selection:
            res.skill_selection_hash = skill_selection.get("selection_hash", "")

        res.expected_verification = {
            "imports_resolve": "required",
            "candidate_tests_pass": "required",
            "boundary_integrity": "required",
            "unexpected_changes": "required"
        }
        
        res.generate_hash()
        return res
class ImpactComparison:
    @staticmethod
    def compare_planned_vs_simulated(planned_files: List[str], simulated_files: List[str]) -> str:
        planned = set(planned_files)
        simulated = set(simulated_files)
        if simulated == planned:
            return "MATCH"
        if simulated - planned:
            return "SIMULATION_EXPANDED_SCOPE"
        return "SIMULATION_CONFLICT"

    @staticmethod
    def compare_simulated_vs_observed(simulated_files: List[str], observed_files: List[str], boundary: List[str] = None) -> str:
        simulated = set(simulated_files)
        observed = set(observed_files)
        
        if boundary:
            out_of_bounds = observed - set(boundary)
            if out_of_bounds:
                return "UNEXPECTED"
                
        if simulated == observed:
            return "MATCH"
        if observed - simulated:
            return "SIMULATION_UNDERESTIMATED"
        if simulated - observed:
            return "SIMULATION_OVERESTIMATED"
        return "UNEXPECTED"



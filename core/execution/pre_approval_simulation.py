import hashlib
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

from core.execution.candidate_binding import CandidateBindingResult
from core.execution.transformation_graph import TransformationExecutionGraph
from core.execution.sandbox import ExecutionSandbox
from core.execution.operation_registry import OperationRegistry

@dataclass
class PredictedEffect:
    target: str
    operation: str
    before_state: str
    predicted_state: str
    evidence: str
    confidence: str

@dataclass
class SimulationConflict:
    type: str
    explanation: str
    blocking: bool

@dataclass
class ValidationStatus:
    status: str
    details: str

@dataclass
class GraphSimulationResult:
    candidate_hash: str
    selection_hash: str
    specification_hash: str
    graph_hash: str
    simulation_hash: str = ""
    
    predicted_effects: List[PredictedEffect] = field(default_factory=list)
    conflicts: List[SimulationConflict] = field(default_factory=list)
    unknowns: List[dict] = field(default_factory=list)
    
    operation_validation: ValidationStatus = field(default_factory=lambda: ValidationStatus("UNKNOWN", ""))
    boundary_validation: ValidationStatus = field(default_factory=lambda: ValidationStatus("UNKNOWN", ""))
    policy_validation: ValidationStatus = field(default_factory=lambda: ValidationStatus("UNKNOWN", ""))
    
    def generate_hash(self) -> str:
        payload = {
            "graph_hash": self.graph_hash,
            "candidate_hash": self.candidate_hash,
            "selection_hash": self.selection_hash,
            "effects": sorted([f"{e.target}:{e.operation}:{e.predicted_state}" for e in self.predicted_effects]),
            "conflicts": sorted([f"{c.type}:{c.blocking}" for c in self.conflicts]),
            "unknowns": sorted([f"{u['code']}:{u.get('blocking', False)}" for u in self.unknowns]),
            "ops": self.operation_validation.status,
            "boundary": self.boundary_validation.status,
            "policy": self.policy_validation.status
        }
        self.simulation_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        return self.simulation_hash

class GraphSimulator:
    def __init__(self, sandbox: ExecutionSandbox, registry: OperationRegistry):
        self.sandbox = sandbox
        self.registry = registry

    def simulate(self, binding: CandidateBindingResult, graph: TransformationExecutionGraph) -> GraphSimulationResult:
        result = GraphSimulationResult(
            candidate_hash=binding.candidate_hash,
            selection_hash=binding.selection_hash,
            specification_hash=binding.specification_hash,
            graph_hash=binding.graph_hash,
            unknowns=binding.unknowns[:]
        )
        
        op_status = "SUPPORTED_FOR_SIMULATION"
        boundary_status = "ALLOWED"
        policy_status = "ALLOWED" # Simple policy for now
        
        for node_id, node in graph.nodes.items():
            step = node.step
            op = step.operation_contract_type
            
            if op == "NO_OP":
                continue
                
            if op not in self.registry.handlers:
                op_status = "TRANSFORMATION_UNSUPPORTED"
                result.conflicts.append(SimulationConflict("OPERATION_CONFLICT", f"Unsupported operation: {op}", True))
                continue
                
            sources = []
            destinations = []
            for out in step.outputs:
                destinations.append(out.path)
                
            # Assume sandbox requires capability=op for our context
            for out in step.outputs:
                auth = self.sandbox.authorize_operation(op, op, sources, [out.path])
                if "REJECTED" in auth:
                    boundary_status = "BOUNDARY_VIOLATION"
                    result.conflicts.append(SimulationConflict("BOUNDARY_CONFLICT", auth, True))
                    break
                    
            for out in step.outputs:
                result.predicted_effects.append(PredictedEffect(
                    target=out.path,
                    operation=op,
                    before_state="UNKNOWN",
                    predicted_state=f"MODIFIED_BY_{op.upper()}",
                    evidence=f"Graph step {step.step_id}",
                    confidence="INFERRED"
                ))
                
        result.operation_validation.status = op_status
        result.boundary_validation.status = boundary_status
        result.policy_validation.status = policy_status
        
        if result.operation_validation.status == "TRANSFORMATION_UNSUPPORTED":
            result.conflicts.append(SimulationConflict("OPERATION_CONFLICT", "Operations not supported", True))
            
        result.generate_hash()
        return result

class PreApprovalValidator:
    def validate(self, sim_result: GraphSimulationResult) -> str:
        if sim_result.operation_validation.status != "SUPPORTED_FOR_SIMULATION":
            return "SIMULATION_UNSUPPORTED"
            
        if sim_result.boundary_validation.status != "ALLOWED":
            return "SIMULATION_BLOCKED"
            
        if sim_result.policy_validation.status != "ALLOWED":
            return "SIMULATION_BLOCKED"
            
        for c in sim_result.conflicts:
            if c.blocking:
                return "SIMULATION_CONFLICT"
                
        for u in sim_result.unknowns:
            if u.get("blocking", False):
                return "SIMULATION_BLOCKED"
                
        if not sim_result.simulation_hash:
            return "SIMULATION_BLOCKED"
            
        return "READY_FOR_APPROVAL"

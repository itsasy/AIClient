import hashlib
import json
from dataclasses import dataclass, field
from typing import List, Optional

from core.execution.candidates import TransformationCandidate, CandidateSelectionRecommendation
from core.execution.specification import TransformationSpecification
from core.execution.transformation_graph import TransformationExecutionGraph, TransformationExecutionGraphBuilder, TransformationGraphValidator
from core.execution.operation_registry import OperationRegistry

@dataclass
class CandidateSelection:
    selected_candidate_id: str
    selected_candidate_hash: str
    comparison_hash: str
    selection_basis: str
    selection_hash: str = ""

    def generate_hash(self) -> str:
        payload = {
            "selected_candidate_id": self.selected_candidate_id,
            "selected_candidate_hash": self.selected_candidate_hash,
            "comparison_hash": self.comparison_hash,
            "selection_basis": self.selection_basis
        }
        self.selection_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        return self.selection_hash

@dataclass
class CandidateBindingIssue:
    code: str
    explanation: str

@dataclass
class CandidateBindingResult:
    candidate_hash: str
    selection_hash: str
    specification_hash: str
    graph_hash: str
    binding_status: str # BOUND, CANDIDATE_BINDING_BLOCKED, etc.
    binding_issues: List[CandidateBindingIssue] = field(default_factory=list)
    unknowns: List[dict] = field(default_factory=list)

@dataclass
class PreSimulationValidation:
    status: str # READY_FOR_SIMULATION, NOT_READY_FOR_SIMULATION
    reasons: List[str] = field(default_factory=list)

class CandidateExecutionGraphBinder:
    def __init__(self, registry: OperationRegistry, graph_builder: TransformationExecutionGraphBuilder, graph_validator: TransformationGraphValidator):
        self.registry = registry
        self.graph_builder = graph_builder
        self.graph_validator = graph_validator

    def select_candidate(self, candidate_id: str, candidate: TransformationCandidate, comparison_hash: str, basis: str) -> CandidateSelection:
        if not candidate_id or candidate.candidate_id != candidate_id:
            raise ValueError("CANDIDATE_NOT_FOUND or CANDIDATE_HASH_MISMATCH")
            
        selection = CandidateSelection(
            selected_candidate_id=candidate_id,
            selected_candidate_hash=candidate.candidate_hash,
            comparison_hash=comparison_hash,
            selection_basis=basis
        )
        selection.generate_hash()
        return selection

    def bind(self, selection: CandidateSelection, candidate: TransformationCandidate, spec: TransformationSpecification) -> CandidateBindingResult:
        result = CandidateBindingResult(
            candidate_hash=candidate.candidate_hash,
            selection_hash=selection.selection_hash,
            specification_hash=spec.specification_hash,
            graph_hash="",
            binding_status="BOUND"
        )
        
        # 1. Identity validation
        if candidate.candidate_hash != selection.selected_candidate_hash:
            result.binding_status = "CANDIDATE_HASH_MISMATCH"
            result.binding_issues.append(CandidateBindingIssue("CANDIDATE_HASH_MISMATCH", "Selection hash does not match candidate"))
            return result
            
        if candidate.evidence and candidate.evidence.specification_hash != spec.specification_hash:
            result.binding_status = "CANDIDATE_SPECIFICATION_MISMATCH"
            result.binding_issues.append(CandidateBindingIssue("CANDIDATE_SPECIFICATION_MISMATCH", "Candidate specification hash mismatch"))
            return result

        if candidate.status == "CANDIDATE_BLOCKED":
            result.binding_status = "CANDIDATE_BINDING_BLOCKED"
            result.binding_issues.append(CandidateBindingIssue("CANDIDATE_BLOCKED", "Candidate is blocked"))
            return result

        # 2. Unknown Propagation
        for u in candidate.unknowns:
            result.unknowns.append({"code": u.code, "explanation": u.explanation, "blocking": u.blocking})
            if u.blocking:
                result.binding_status = "CANDIDATE_BINDING_BLOCKED"
                result.binding_issues.append(CandidateBindingIssue("BLOCKING_UNKNOWN", f"Unknown is blocking: {u.code}"))

        if result.binding_status != "BOUND":
            return result

        # 3. Target and Operation validation
        # P25 already verified this in generator, but P26 acts as a gatekeeper.
        for item in candidate.items:
            for t in item.targets:
                if t.confidence == "UNKNOWN":
                    # For this test, let's say UNKNOWN target is blocking for binding
                    result.binding_status = "CANDIDATE_TARGET_UNVERIFIED"
                    result.binding_issues.append(CandidateBindingIssue("CANDIDATE_TARGET_UNVERIFIED", f"Target {t.target_id} is unverified"))
                    return result
            
            for op in item.required_operations:
                if op != "NO_OP" and op not in self.registry.handlers:
                    result.binding_status = "TRANSFORMATION_UNSUPPORTED"
                    result.binding_issues.append(CandidateBindingIssue("TRANSFORMATION_UNSUPPORTED", f"Operation {op} unsupported"))
                    return result

        # 4. Filter Specification for Graph Builder
        filtered_items = [i for i in spec.items if i.candidate_id == candidate.candidate_id]
        if not filtered_items:
            result.binding_status = "CANDIDATE_SPECIFICATION_MISMATCH"
            result.binding_issues.append(CandidateBindingIssue("CANDIDATE_SPECIFICATION_MISMATCH", "No spec items for candidate"))
            return result
            
        # We create an ephemeral specification to pass to P22 Graph Builder.
        # This keeps P22 untouched. (READ_ONLY_COMPATIBLE)
        filtered_spec = TransformationSpecification(
            proposal_hash=spec.proposal_hash,
            candidate_id=candidate.candidate_id,
            requirements=spec.requirements,
            specification_hash=spec.specification_hash,
            boundary_hash=spec.boundary_hash,
            policy_hash=spec.policy_hash
        )
        filtered_spec.items = filtered_items

        # 5. Build and validate graph
        try:
            graph = self.graph_builder.build(filtered_spec)
        except Exception as e:
            result.binding_status = "GRAPH_BUILD_ERROR"
            result.binding_issues.append(CandidateBindingIssue("GRAPH_BUILD_ERROR", str(e)))
            return result

        valid_status = self.graph_validator.validate(graph)
        if valid_status != "VALID":
            result.binding_status = "GRAPH_CANDIDATE_MISMATCH"
            result.binding_issues.append(CandidateBindingIssue("GRAPH_INVALID", f"Graph validator returned {valid_status}"))
            return result

        result.graph_hash = graph.graph_hash
        return result


class PreSimulationValidator:
    def validate(self, binding_result: CandidateBindingResult) -> PreSimulationValidation:
        reasons = []
        if binding_result.binding_status != "BOUND":
            reasons.append(f"Binding status is not BOUND: {binding_result.binding_status}")
            
        if not binding_result.graph_hash:
            reasons.append("Missing graph_hash")
            
        if any(u.get("blocking") for u in binding_result.unknowns):
            reasons.append("Contains blocking unknowns")

        if reasons:
            return PreSimulationValidation("NOT_READY_FOR_SIMULATION", reasons)
        return PreSimulationValidation("READY_FOR_SIMULATION", [])


import hashlib
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

from core.execution.pre_approval_simulation import GraphSimulationResult
from core.execution.candidates import TransformationCandidate

@dataclass
class ApprovalRequest:
    proposal_hash: str
    specification_hash: str
    structural_analysis_hash: str
    semantic_analysis_hash: str
    candidate_hash: str
    selection_hash: str
    graph_hash: str
    simulation_hash: str
    candidate_id: str
    selection_id: str
    
    scope: List[str]
    required_operations: List[str]
    predicted_effects: List[dict]
    risk: str
    impact: str
    unknowns: List[dict]
    simulation_status: str
    
    approval_request_hash: str = ""
    
    def generate_hash(self) -> str:
        payload = {
            "proposal_hash": self.proposal_hash,
            "specification_hash": self.specification_hash,
            "structural_analysis_hash": self.structural_analysis_hash,
            "semantic_analysis_hash": self.semantic_analysis_hash,
            "candidate_hash": self.candidate_hash,
            "selection_hash": self.selection_hash,
            "graph_hash": self.graph_hash,
            "simulation_hash": self.simulation_hash,
            "candidate_id": self.candidate_id,
            "selection_id": self.selection_id,
            "scope": sorted(self.scope),
            "operations": sorted(self.required_operations),
            "effects": sorted([f"{e['target']}:{e['operation']}:{e['predicted_state']}" for e in self.predicted_effects]),
            "risk": self.risk,
            "impact": self.impact,
            "unknowns": sorted([f"{u['code']}:{u.get('blocking', False)}" for u in self.unknowns]),
            "simulation_status": self.simulation_status
        }
        self.approval_request_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        return self.approval_request_hash

@dataclass
class ApprovalDecision:
    approval_request_hash: str
    decision: str # APPROVED, REJECTED, INVALID
    approver_reference: str
    decision_basis: str
    approval_decision_hash: str = ""
    
    def generate_hash(self) -> str:
        payload = {
            "request_hash": self.approval_request_hash,
            "decision": self.decision,
            "approver": self.approver_reference,
            "basis": self.decision_basis
        }
        self.approval_decision_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        return self.approval_decision_hash

@dataclass
class AuthorizationEvidence:
    status: str # AUTHORIZATION_VALID, AUTHORIZATION_INVALID
    handoff: str # HANDOFF_TO_WORKFLOW, NONE
    approval_decision_hash: str
    approval_request_hash: str
    issues: List[str] = field(default_factory=list)

class ApprovalGate:
    def create_request(self, 
                      candidate: TransformationCandidate, 
                      selection_id: str, 
                      simulation: GraphSimulationResult, 
                      simulation_status: str,
                      risk: str, 
                      impact: str) -> ApprovalRequest:
                      
        scope = []
        operations = []
        for i in candidate.items:
            for t in i.targets:
                if t.target_id not in scope:
                    scope.append(t.target_id)
            for o in i.required_operations:
                if o not in operations:
                    operations.append(o)
                    
        req = ApprovalRequest(
            proposal_hash=candidate.evidence.proposal_hash if candidate.evidence else "",
            specification_hash=candidate.evidence.specification_hash if candidate.evidence else "",
            structural_analysis_hash=candidate.evidence.structural_analysis_hash if candidate.evidence else "",
            semantic_analysis_hash=candidate.evidence.semantic_analysis_hash if candidate.evidence else "",
            candidate_hash=candidate.candidate_hash,
            selection_hash=simulation.selection_hash,
            graph_hash=simulation.graph_hash,
            simulation_hash=simulation.simulation_hash,
            candidate_id=candidate.candidate_id,
            selection_id=selection_id,
            scope=scope,
            required_operations=operations,
            predicted_effects=[{"target": e.target, "operation": e.operation, "predicted_state": e.predicted_state} for e in simulation.predicted_effects],
            risk=risk,
            impact=impact,
            unknowns=simulation.unknowns,
            simulation_status=simulation_status
        )
        req.generate_hash()
        return req

    def approve(self, request: ApprovalRequest, approver_reference: str, basis: str) -> ApprovalDecision:
        decision = ApprovalDecision(
            approval_request_hash=request.approval_request_hash,
            decision="APPROVED",
            approver_reference=approver_reference,
            decision_basis=basis
        )
        decision.generate_hash()
        return decision

    def reject(self, request: ApprovalRequest, approver_reference: str, basis: str) -> ApprovalDecision:
        decision = ApprovalDecision(
            approval_request_hash=request.approval_request_hash,
            decision="REJECTED",
            approver_reference=approver_reference,
            decision_basis=basis
        )
        decision.generate_hash()
        return decision

    def validate(self, decision: ApprovalDecision, request: ApprovalRequest, 
                 candidate: TransformationCandidate, simulation: GraphSimulationResult,
                 simulation_status: str) -> AuthorizationEvidence:
                 
        issues = []
        if decision.decision != "APPROVED":
            issues.append(f"Decision is {decision.decision}")
            
        if decision.approval_request_hash != request.approval_request_hash:
            issues.append("APPROVAL_REQUEST_MISMATCH")
            
        if request.candidate_hash != candidate.candidate_hash:
            issues.append("APPROVAL_ARTIFACT_MISMATCH (Candidate)")
            
        if request.simulation_hash != simulation.simulation_hash:
            issues.append("APPROVAL_ARTIFACT_MISMATCH (Simulation)")
            
        if simulation_status != "READY_FOR_APPROVAL":
            issues.append("SIMULATION_NOT_READY")
            
        if request.simulation_status != "READY_FOR_APPROVAL":
            issues.append("APPROVAL_REQUEST_INVALID_SIMULATION_STATUS")
            
        # Scope and ops mismatch
        actual_scope = []
        actual_ops = []
        for i in candidate.items:
            for t in i.targets:
                if t.target_id not in actual_scope:
                    actual_scope.append(t.target_id)
            for o in i.required_operations:
                if o not in actual_ops:
                    actual_ops.append(o)
                    
        if sorted(request.scope) != sorted(actual_scope):
            issues.append("APPROVAL_SCOPE_MISMATCH")
            
        if sorted(request.required_operations) != sorted(actual_ops):
            issues.append("APPROVAL_OPERATION_MISMATCH")
            
        actual_effects = [{"target": e.target, "operation": e.operation, "predicted_state": e.predicted_state} for e in simulation.predicted_effects]
        
        # Sort both before comparing
        def sort_effects(effs):
            return sorted([f"{e['target']}:{e['operation']}:{e['predicted_state']}" for e in effs])
            
        if sort_effects(request.predicted_effects) != sort_effects(actual_effects):
            issues.append("APPROVAL_ARTIFACT_MISMATCH (Effects)")
            
        for u in request.unknowns:
            if u.get("blocking"):
                issues.append("BLOCKING_UNKNOWN")
                
        if issues:
            return AuthorizationEvidence(
                status="AUTHORIZATION_INVALID",
                handoff="NONE",
                approval_decision_hash=decision.approval_decision_hash,
                approval_request_hash=request.approval_request_hash,
                issues=issues
            )
            
        return AuthorizationEvidence(
            status="AUTHORIZATION_VALID",
            handoff="HANDOFF_TO_WORKFLOW",
            approval_decision_hash=decision.approval_decision_hash,
            approval_request_hash=request.approval_request_hash
        )

import hashlib
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import uuid

from core.execution.approval_gate import AuthorizationEvidence, ApprovalDecision, ApprovalRequest
from core.execution.pre_approval_simulation import GraphSimulationResult
from core.execution.candidates import TransformationCandidate

@dataclass
class WorkflowArtifactBinding:
    proposal_hash: str
    specification_hash: str
    structural_analysis_hash: str
    semantic_analysis_hash: str
    candidate_hash: str
    selection_hash: str
    graph_hash: str
    simulation_hash: str
    approval_request_hash: str
    approval_decision_hash: str

@dataclass
class WorkflowBindingIssue:
    code: str
    explanation: str

@dataclass
class WorkflowHandoffRequest:
    workflow_id: str
    transaction_id: str
    artifact_binding: WorkflowArtifactBinding
    scope: List[str]
    required_operations: List[str]
    predicted_effects: List[dict]
    risk: str
    unknowns: List[dict]
    
    workflow_handoff_hash: str = ""
    
    def generate_hash(self) -> str:
        payload = {
            "workflow_id": self.workflow_id,
            "transaction_id": self.transaction_id,
            "proposal_hash": self.artifact_binding.proposal_hash,
            "specification_hash": self.artifact_binding.specification_hash,
            "structural_analysis_hash": self.artifact_binding.structural_analysis_hash,
            "semantic_analysis_hash": self.artifact_binding.semantic_analysis_hash,
            "candidate_hash": self.artifact_binding.candidate_hash,
            "selection_hash": self.artifact_binding.selection_hash,
            "graph_hash": self.artifact_binding.graph_hash,
            "simulation_hash": self.artifact_binding.simulation_hash,
            "approval_request_hash": self.artifact_binding.approval_request_hash,
            "approval_decision_hash": self.artifact_binding.approval_decision_hash,
            "scope": sorted(self.scope),
            "operations": sorted(self.required_operations),
            "effects": sorted([f"{e['target']}:{e['operation']}:{e['predicted_state']}" for e in self.predicted_effects]),
            "risk": self.risk,
            "unknowns": sorted([f"{u['code']}:{u.get('blocking', False)}" for u in self.unknowns])
        }
        self.workflow_handoff_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        return self.workflow_handoff_hash

@dataclass
class AuthorizedWorkflowContext:
    handoff_hash: str
    transaction_id: str
    workflow_id: str

@dataclass
class ExecutionReadyContract:
    execution_ready_hash: str
    status: str
    authorized_context: AuthorizedWorkflowContext

@dataclass
class HandoffValidationResult:
    status: str # HANDOFF_VALID, HANDOFF_INVALID, HANDOFF_BLOCKED, WORKFLOW_BINDING_UNSUPPORTED
    issues: List[WorkflowBindingIssue] = field(default_factory=list)

class WorkflowHandoffGate:
    def prepare_handoff(self, 
                        evidence: AuthorizationEvidence,
                        request: ApprovalRequest,
                        decision: ApprovalDecision,
                        workflow_id: str = "",
                        transaction_id: str = "") -> WorkflowHandoffRequest:
                        
        if not workflow_id:
            workflow_id = str(uuid.uuid4())
        if not transaction_id:
            transaction_id = str(uuid.uuid4())
            
        binding = WorkflowArtifactBinding(
            proposal_hash=request.proposal_hash,
            specification_hash=request.specification_hash,
            structural_analysis_hash=request.structural_analysis_hash,
            semantic_analysis_hash=request.semantic_analysis_hash,
            candidate_hash=request.candidate_hash,
            selection_hash=request.selection_hash,
            graph_hash=request.graph_hash,
            simulation_hash=request.simulation_hash,
            approval_request_hash=request.approval_request_hash,
            approval_decision_hash=decision.approval_decision_hash
        )
        
        handoff = WorkflowHandoffRequest(
            workflow_id=workflow_id,
            transaction_id=transaction_id,
            artifact_binding=binding,
            scope=request.scope[:],
            required_operations=request.required_operations[:],
            predicted_effects=request.predicted_effects[:],
            risk=request.risk,
            unknowns=request.unknowns[:]
        )
        handoff.generate_hash()
        return handoff

    def validate_handoff(self, 
                         handoff: WorkflowHandoffRequest,
                         evidence: AuthorizationEvidence,
                         request: ApprovalRequest,
                         decision: ApprovalDecision,
                         candidate: TransformationCandidate,
                         simulation: GraphSimulationResult) -> HandoffValidationResult:
                         
        issues = []
        if evidence.status != "AUTHORIZATION_VALID":
            issues.append(WorkflowBindingIssue("AUTHORIZATION_INVALID", "Evidence is not valid"))
            
        if evidence.handoff != "HANDOFF_TO_WORKFLOW":
            issues.append(WorkflowBindingIssue("HANDOFF_TOKEN_MISMATCH", "Invalid handoff token"))
            
        if decision.decision != "APPROVED":
            issues.append(WorkflowBindingIssue("APPROVAL_NOT_VALID", "Decision is not APPROVED"))
            
        if handoff.artifact_binding.approval_request_hash != request.approval_request_hash:
            issues.append(WorkflowBindingIssue("APPROVAL_REQUEST_MISMATCH", "Approval request hash mismatch"))
            
        if handoff.artifact_binding.approval_decision_hash != decision.approval_decision_hash:
            issues.append(WorkflowBindingIssue("APPROVAL_DECISION_MISMATCH", "Approval decision hash mismatch"))
            
        if handoff.artifact_binding.candidate_hash != candidate.candidate_hash:
            issues.append(WorkflowBindingIssue("ARTIFACT_HASH_MISMATCH", "Candidate hash mismatch"))
            
        if handoff.artifact_binding.selection_hash != simulation.selection_hash:
            issues.append(WorkflowBindingIssue("ARTIFACT_HASH_MISMATCH", "Selection hash mismatch"))
            
        if handoff.artifact_binding.graph_hash != simulation.graph_hash:
            issues.append(WorkflowBindingIssue("GRAPH_ARTIFACT_MISMATCH", "Graph hash mismatch"))
            
        if handoff.artifact_binding.simulation_hash != simulation.simulation_hash:
            issues.append(WorkflowBindingIssue("ARTIFACT_HASH_MISMATCH", "Simulation hash mismatch"))
            
        # Scope and operation matching
        if sorted(handoff.scope) != sorted(request.scope):
            issues.append(WorkflowBindingIssue("AUTHORIZED_SCOPE_MISMATCH", "Scope mismatch"))
            
        if sorted(handoff.required_operations) != sorted(request.required_operations):
            issues.append(WorkflowBindingIssue("AUTHORIZED_OPERATION_MISMATCH", "Operation mismatch"))
            
        if handoff.risk != request.risk:
            issues.append(WorkflowBindingIssue("AUTHORIZED_RISK_MISMATCH", "Risk mismatch"))
            
        def sort_effects(effs):
            return sorted([f"{e['target']}:{e['operation']}:{e['predicted_state']}" for e in effs])
            
        if sort_effects(handoff.predicted_effects) != sort_effects(request.predicted_effects):
            issues.append(WorkflowBindingIssue("PREDICTED_EFFECT_MISMATCH", "Effect mismatch"))
            
        for u in handoff.unknowns:
            if u.get("blocking"):
                issues.append(WorkflowBindingIssue("BLOCKING_UNKNOWN", "Blocking unknown present"))
                
        if issues:
            return HandoffValidationResult(status="HANDOFF_BLOCKED", issues=issues)
            
        return HandoffValidationResult(status="HANDOFF_VALID", issues=[])

    def create_execution_ready_contract(self, handoff: WorkflowHandoffRequest, validation: HandoffValidationResult) -> ExecutionReadyContract:
        if validation.status != "HANDOFF_VALID":
            return ExecutionReadyContract(execution_ready_hash="", status="NOT_READY", authorized_context=None)
            
        ctx = AuthorizedWorkflowContext(
            handoff_hash=handoff.workflow_handoff_hash,
            transaction_id=handoff.transaction_id,
            workflow_id=handoff.workflow_id
        )
        
        payload = f"{ctx.handoff_hash}:{ctx.transaction_id}:{ctx.workflow_id}:READY_FOR_EXECUTION"
        er_hash = hashlib.sha256(payload.encode()).hexdigest()
        
        return ExecutionReadyContract(
            execution_ready_hash=er_hash,
            status="READY_FOR_EXECUTION",
            authorized_context=ctx
        )

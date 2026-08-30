from dataclasses import dataclass, field
from typing import Any, List, Dict
from core.discovery.transformation import TransformationPlan, CandidateTransformationPlan

@dataclass
class ActionPolicy:
    action: str
    decision: str  # ALLOW, ALLOW_WITH_VALIDATION, REQUIRE_APPROVAL, DENY
    reason: str
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "decision": self.decision,
            "reason": self.reason
        }

@dataclass
class Precondition:
    type: str
    evidence: str
    verified: bool = False
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "evidence": self.evidence,
            "verified": self.verified
        }

@dataclass
class Postcondition:
    type: str
    required: bool = True
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "required": self.required
        }

@dataclass
class VerificationPlan:
    preflight: List[str] = field(default_factory=list)
    transformation: List[str] = field(default_factory=list)
    postflight: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "preflight": self.preflight,
            "transformation": self.transformation,
            "postflight": self.postflight
        }

@dataclass
class RollbackStrategy:
    required: bool = True
    strategy: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "required": self.required,
            "strategy": self.strategy
        }

@dataclass
class ApprovalRequirement:
    required: bool = False
    reasons: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "required": self.required,
            "reasons": self.reasons
        }

@dataclass
class PolicyDecision:
    candidate: str
    decision: str
    reasons: List[str] = field(default_factory=list)
    allowed: List[str] = field(default_factory=list)
    approval_required: List[str] = field(default_factory=list)
    denied: List[str] = field(default_factory=list)
    preconditions: List[Precondition] = field(default_factory=list)
    postconditions: List[Postcondition] = field(default_factory=list)
    verification: VerificationPlan = field(default_factory=VerificationPlan)
    rollback: RollbackStrategy = field(default_factory=RollbackStrategy)
    approval: ApprovalRequirement = field(default_factory=ApprovalRequirement)
    confidence: str = "unknown"
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate": self.candidate,
            "decision": self.decision,
            "reasons": self.reasons,
            "allowed": self.allowed,
            "approval_required": self.approval_required,
            "denied": self.denied,
            "preconditions": [p.to_dict() for p in self.preconditions],
            "postconditions": [p.to_dict() for p in self.postconditions],
            "verification": self.verification.to_dict(),
            "rollback": self.rollback.to_dict(),
            "approval": self.approval.to_dict(),
            "confidence": self.confidence
        }

@dataclass
class TransformationPolicy:
    decisions: List[PolicyDecision] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "decisions": [d.to_dict() for d in self.decisions]
        }


class TransformationPolicyEvaluator:
    def __init__(self, plan: TransformationPlan):
        self.plan = plan
        self.policy_result = TransformationPolicy()
        
    def evaluate(self) -> TransformationPolicy:
        for candidate_plan in self.plan.candidates:
            decision = self._evaluate_candidate(candidate_plan)
            self.policy_result.decisions.append(decision)
        return self.policy_result

    def _evaluate_candidate(self, cand: CandidateTransformationPlan) -> PolicyDecision:
        pd = PolicyDecision(candidate=cand.candidate, decision="UNKNOWN")
        
        is_blocked = cand.extraction_readiness == "BLOCKED"
        requires_adaptation = cand.extraction_readiness == "REQUIRES_ADAPTATION"
        
        # Determine global decision
        if is_blocked:
            pd.decision = "DENY"
            pd.reasons.append("Candidate is blocked from extraction")
            for risk in cand.risks:
                pd.reasons.append(risk.type)
        elif requires_adaptation:
            pd.decision = "REQUIRE_APPROVAL"
            pd.reasons.append("Adaptation required before extraction")
        elif cand.extraction_readiness == "READY_WITH_VALIDATION":
            pd.decision = "ALLOW_WITH_VALIDATION"
            pd.reasons.append("Requires pre- and post-validation")
        else:
            pd.decision = "ALLOW_WITH_VALIDATION"  # Mutative actions always require at least validation
            pd.reasons.append("Candidate is isolated and ready")
            
        # Action Polices
        actions = {
            "inspect_boundary": "ALLOW",
            "run_tests": "ALLOW",
            "run_analysis": "ALLOW",
            "move_files": "DENY" if is_blocked else "REQUIRE_APPROVAL",
            "copy_files": "DENY" if is_blocked else "REQUIRE_APPROVAL",
            "create_adapter": "DENY" if is_blocked else "REQUIRE_APPROVAL",
            "rewrite_imports": "DENY" if is_blocked else "REQUIRE_APPROVAL",
            "delete_source": "DENY",  # Always deny destructive deletions for now
        }
        
        for action, decision in actions.items():
            if decision == "ALLOW":
                pd.allowed.append(action)
            elif decision == "REQUIRE_APPROVAL":
                pd.approval_required.append(action)
            elif decision == "DENY":
                pd.denied.append(action)
                
        # Approval Requirements
        if not is_blocked:
            pd.approval.required = True
            if requires_adaptation:
                pd.approval.reasons.append("introduces_adapter")
            if cand.dependencies:
                pd.approval.reasons.append("modifies_shared_dependency")
            if not pd.approval.reasons:
                pd.approval.reasons.append("mutates_filesystem")
                
        # Preconditions
        pd.preconditions.append(Precondition(type="boundary_verified", evidence="Static analysis boundary mapped"))
        if len(cand.dependencies) > 0:
            pd.preconditions.append(Precondition(type="dependencies_resolved", evidence="Dependencies mapped in TransformationPlan"))
        if False: #cand.validation removed in later iterations
            pd.preconditions.append(Precondition(type="tests_available", evidence="Test execution required"))
        if requires_adaptation:
            pd.preconditions.append(Precondition(type="adaptation_points_defined", evidence=f"{len(cand.adaptation_points)} points mapped"))
            
        # Postconditions
        pd.postconditions.append(Postcondition(type="imports_resolve", required=True))
        pd.postconditions.append(Postcondition(type="candidate_tests_pass", required=True))
        pd.postconditions.append(Postcondition(type="no_forbidden_files_modified", required=True))
        if cand.dependencies:
            pd.postconditions.append(Postcondition(type="dependency_contract_preserved", required=True))
            
        # Verification Plan
        pd.verification.preflight = ["snapshot_boundary", "record_test_baseline"]
        pd.verification.transformation = ["relocate_candidate"]
        if requires_adaptation:
            pd.verification.transformation.insert(0, "apply_adaptations")
        pd.verification.postflight = ["import_check", "candidate_tests", "build_check"]
        if cand.dependencies:
            pd.verification.postflight.append("dependency_check")
            
        # Rollback Strategy
        pd.rollback.required = True
        pd.rollback.strategy = ["restore_moved_files", "restore_imports"]
        if requires_adaptation:
            pd.rollback.strategy.append("remove_generated_adapter")
            
        pd.confidence = 'unknown'
        return pd



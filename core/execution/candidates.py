from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import hashlib
import json

@dataclass
class CandidateEvidence:
    proposal_hash: str
    specification_hash: str
    structural_analysis_hash: str
    semantic_analysis_hash: str
    traceability_links: List[str] = field(default_factory=list)

@dataclass
class CandidateUnknown:
    code: str
    explanation: str
    blocking: bool = False

@dataclass
class CandidateImpact:
    files_affected: List[str] = field(default_factory=list)
    modules_affected: List[str] = field(default_factory=list)
    symbols_affected: List[str] = field(default_factory=list)
    imports_affected: List[str] = field(default_factory=list)
    dependencies_affected: List[str] = field(default_factory=list)
    interfaces_affected: List[str] = field(default_factory=list)
    potential_conflicts: List[str] = field(default_factory=list)
    indirect_impact: List[str] = field(default_factory=list)
    unknown_impact: List[str] = field(default_factory=list)

@dataclass
class CandidateTarget:
    target_type: str # module, file, symbol, interface
    target_id: str
    confidence: str # CONFIRMED, INFERRED, UNKNOWN

@dataclass
class CandidateRisk:
    score: str # LOW, MEDIUM, HIGH, BLOCKED
    factors: List[str] = field(default_factory=list)

@dataclass
class CandidateItem:
    item_id: str
    action_type: str # REUSE, ADAPT, EXTEND, CREATE, MODIFY, DELETE, MOVE, RENAME
    targets: List[CandidateTarget] = field(default_factory=list)
    required_operations: List[str] = field(default_factory=list)

@dataclass
class TransformationCandidate:
    candidate_id: str
    items: List[CandidateItem] = field(default_factory=list)
    evidence: Optional[CandidateEvidence] = None
    impact: Optional[CandidateImpact] = None
    risk: Optional[CandidateRisk] = None
    unknowns: List[CandidateUnknown] = field(default_factory=list)
    status: str = "VALID" # VALID, CANDIDATE_UNCERTAIN, CANDIDATE_BLOCKED, CANDIDATE_TRACEABILITY_FAILURE, TRANSFORMATION_UNSUPPORTED
    candidate_hash: str = ""

    def generate_hash(self) -> str:
        payload = {
            "candidate_id": self.candidate_id,
            "evidence": {
                "prop": self.evidence.proposal_hash if self.evidence else "",
                "spec": self.evidence.specification_hash if self.evidence else "",
                "struct": self.evidence.structural_analysis_hash if self.evidence else "",
                "sem": self.evidence.semantic_analysis_hash if self.evidence else "",
                "trace": sorted(self.evidence.traceability_links) if self.evidence else []
            },
            "items": [],
            "impact": {},
            "risk": self.risk.score if self.risk else "UNKNOWN",
            "status": self.status,
            "unknowns": sorted([f"{u.code}:{u.blocking}" for u in self.unknowns])
        }

        for item in sorted(self.items, key=lambda x: x.item_id):
            payload["items"].append({
                "id": item.item_id,
                "action": item.action_type,
                "ops": sorted(item.required_operations),
                "targets": sorted([f"{t.target_type}:{t.target_id}:{t.confidence}" for t in item.targets])
            })

        if self.impact:
            payload["impact"] = {
                "files": sorted(self.impact.files_affected),
                "modules": sorted(self.impact.modules_affected),
                "symbols": sorted(self.impact.symbols_affected),
                "deps": sorted(self.impact.dependencies_affected),
                "indirect": sorted(self.impact.indirect_impact),
                "unknown": sorted(self.impact.unknown_impact)
            }
            
        self.candidate_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        return self.candidate_hash

@dataclass
class CandidateComparison:
    comparisons: Dict[str, Any] = field(default_factory=dict)
    cross_candidate_dependencies: List[str] = field(default_factory=list)
    cross_candidate_conflicts: List[str] = field(default_factory=list)

@dataclass
class CandidateSelectionRecommendation:
    recommended_candidate_id: str
    recommendation_basis: str
    supporting_evidence: str
    risk_basis: str
    impact_basis: str
    unknown_basis: str
    status: str = "RECOMMENDED" # RECOMMENDED, NOT_RECOMMENDED, TIE

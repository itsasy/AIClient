import hashlib
import json
import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

VALID_ACTION_CATEGORIES = {"REUSE", "MODIFY", "CREATE", "ADAPT", "DELETE", "MOVE", "RENAME"}

@dataclass
class Requirement:
    req_id: str
    description: str

@dataclass
class ReferenceAnalysis:
    project_path: str
    classifications: Dict[str, str] = field(default_factory=dict) # e.g. {"sales": "REUSE", "products": "ADAPT"}

@dataclass
class ProposalItem:
    item_id: str
    req_id: str
    category: str # MUST be in VALID_ACTION_CATEGORIES
    description: str
    candidate_id: str
    operations: List[str] = field(default_factory=list)

@dataclass
class TransformationProposal:
    proposal_id: str
    intent: str
    objective: str
    scope: List[str] = field(default_factory=list)
    requirements: List[Requirement] = field(default_factory=list)
    items: List[ProposalItem] = field(default_factory=list)
    
    reference_analysis: Optional[ReferenceAnalysis] = None
    
    affected_files: List[str] = field(default_factory=list)
    affected_modules: List[str] = field(default_factory=list)
    affected_symbols: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    
    assumptions: List[str] = field(default_factory=list)
    unknowns: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    rationale: str = ""
    
    status: str = "VALID" # VALID, TRANSFORMATION_UNSUPPORTED, ANALYSIS_INCOMPLETE, REJECTED
    proposal_hash: str = ""

    def generate_hash(self) -> str:
        # Hashes MUST be deterministic. No timestamps, UUIDs, or random orders.
        payload = {
            "intent": self.intent,
            "objective": self.objective,
            "scope": sorted(self.scope),
            "requirements": [{"id": r.req_id, "desc": r.description} for r in sorted(self.requirements, key=lambda x: x.req_id)],
            "items": [{"req_id": i.req_id, "cat": i.category, "desc": i.description, "cand": i.candidate_id, "ops": sorted(i.operations)} for i in sorted(self.items, key=lambda x: x.item_id)],
            "reference": self.reference_analysis.classifications if self.reference_analysis else {},
            "affected_files": sorted(self.affected_files),
            "affected_modules": sorted(self.affected_modules),
            "assumptions": sorted(self.assumptions),
            "unknowns": sorted(self.unknowns),
            "acceptance_criteria": sorted(self.acceptance_criteria)
        }
        self.proposal_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        return self.proposal_hash

class ProposalGenerator:
    def validate_proposal(self, proposal: TransformationProposal) -> TransformationProposal:
        for item in proposal.items:
            if item.category not in VALID_ACTION_CATEGORIES:
                proposal.status = "TRANSFORMATION_UNSUPPORTED"
                proposal.rationale = f"Unsupported category: {item.category}"
                return proposal
                
        # Check subjective acceptance criteria
        subjective_words = ["looks_good", "probably_works"]
        for ac in proposal.acceptance_criteria:
            if any(w in ac.lower() for w in subjective_words):
                proposal.status = "TRANSFORMATION_UNSUPPORTED"
                proposal.rationale = "Subjective acceptance criteria found."
                return proposal
                
        # If any required analysis is marked incomplete
        if "ANALYSIS_INCOMPLETE" in proposal.unknowns:
            proposal.status = "ANALYSIS_INCOMPLETE"
            return proposal
            
        proposal.generate_hash()
        return proposal

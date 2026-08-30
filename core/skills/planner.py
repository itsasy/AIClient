import hashlib
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from core.skills.registry import SkillRegistry
from core.discovery.transformation import MultiCandidateTransformationPlan, CandidateTransformationPlan

@dataclass
class SelectedSkill:
    skill_id: str
    version: str
    implementation_hash: str
    attestation_hash: str
    required_capabilities: List[str]

@dataclass
class SkillSelectionPlan:
    candidate_id: str
    requested_operations: List[str] = field(default_factory=list)
    selected_skills: List[SelectedSkill] = field(default_factory=list)
    required_capabilities: List[str] = field(default_factory=list)
    unavailable_capabilities: List[str] = field(default_factory=list)
    rejected_skills: List[str] = field(default_factory=list)
    selection_reason: str = ""
    registry_snapshot_hash: str = ""
    proposal_hash: str = ""
    specification_hash: str = ""
    selection_hash: str = ""
    status: str = "VALID" # VALID, CAPABILITY_CLOSURE_FAILED, SKILL_CONFLICT, SKILL_SELECTION_REJECTED
    
    def generate_hash(self):
        skills_payload = []
        for s in sorted(self.selected_skills, key=lambda x: x.skill_id):
            skills_payload.append({
                "skill_id": s.skill_id,
                "version": s.version,
                "implementation_hash": s.implementation_hash,
                "attestation_hash": s.attestation_hash,
                "required_capabilities": sorted(s.required_capabilities)
            })
            
        payload = {
            "candidate_id": self.candidate_id,
            "requested_operations": sorted(self.requested_operations),
            "selected_skills": skills_payload,
            "registry_snapshot_hash": self.registry_snapshot_hash,
            "proposal_hash": self.proposal_hash,
            "specification_hash": self.specification_hash
        }
        self.selection_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

class AutonomousSkillPlanner:
    def __init__(self, registry: SkillRegistry):
        self.registry = registry

    def _is_safe_operation(self, operation: str) -> bool:
        forbidden = ["execute_shell", "subprocess", "os.system", "eval", "exec"]
        return operation not in forbidden

    def plan_candidate(self, candidate_plan: CandidateTransformationPlan, proposal_hash: str = "", specification_hash: str = "") -> SkillSelectionPlan:
        # LLM Autonomous Simulation
        operations = list(set([act.operation for act in candidate_plan.actions]))
        registry_info = self.registry.get_discovery_info()
        registry_hash = self.registry.get_snapshot_hash()
        
        plan = SkillSelectionPlan(
            candidate_id=candidate_plan.candidate,
            requested_operations=operations,
            registry_snapshot_hash=registry_hash,
            proposal_hash=proposal_hash,
            specification_hash=specification_hash
        )
        
        # 1. Privilege Escalation Check
        for op in operations:
            if not self._is_safe_operation(op):
                plan.status = "SKILL_SELECTION_REJECTED"
                plan.selection_reason = f"Forbidden operation requested: {op}"
                return plan
        
        # 2. Skill Selection Logic
        needed_caps = set(operations)
        covered_caps = set()
        
        for skill_id, info in registry_info.items():
            skill_caps = set(info["capabilities"])
            useful_caps = skill_caps.intersection(needed_caps)
            
            if useful_caps:
                # Add skill
                sel = SelectedSkill(
                    skill_id=skill_id,
                    version=info["version"],
                    implementation_hash=info["implementation_hash"],
                    attestation_hash=info["attestation_hash"],
                    required_capabilities=list(useful_caps)
                )
                plan.selected_skills.append(sel)
                covered_caps.update(useful_caps)
                
        # 3. Capability Closure Check
        missing = needed_caps - covered_caps
        if missing:
            plan.unavailable_capabilities = list(missing)
            plan.status = "CAPABILITY_CLOSURE_FAILED"
            plan.selection_reason = f"Missing capabilities: {missing}"
            return plan
            
        # 4. Conflict Check
        # For this prototype, if multiple skills offer the same capability and are selected, it's a conflict
        # unless it's managed. For simplicity, we just count.
        cap_counts = {}
        for s in plan.selected_skills:
            for cap in s.required_capabilities:
                cap_counts[cap] = cap_counts.get(cap, 0) + 1
                
        for cap, count in cap_counts.items():
            if count > 1:
                plan.status = "SKILL_CONFLICT"
                plan.selection_reason = f"Multiple skills provide capability {cap}"
                return plan
                
        plan.required_capabilities = list(covered_caps)
        plan.selection_reason = "Skills selected successfully."
        plan.generate_hash()
        return plan

import json
import hashlib
from typing import Dict, List, Optional
from core.skills.models import Skill, CapabilityMatch
from core.skills.identity import SkillIdentity, CapabilityAttestation

class RegisteredSkill:
    def __init__(self, skill: Skill, identity: SkillIdentity, attestation: CapabilityAttestation):
        self.skill = skill
        self.identity = identity
        self.attestation = attestation
        self.status = "VERIFIED"

class SkillRegistry:
    def __init__(self):
        self.skills: Dict[str, RegisteredSkill] = {}
        
    def _generate_mock_hash(self, skill: Skill) -> str:
        return hashlib.sha256(skill.name.encode()).hexdigest()

    def register(self, skill: Skill):
        # Compatibility with older tests
        impl_hash = self._generate_mock_hash(skill)
        man_hash = "mock_manifest_hash"
        
        identity = SkillIdentity(skill.name, skill.name, "1.0", impl_hash, man_hash)
        attestation = CapabilityAttestation(skill.name, "1.0", impl_hash, skill.capabilities)
        attestation.generate_attestation_hash()
        
        if skill.name in self.skills:
            existing = self.skills[skill.name]
            if set(existing.attestation.capabilities) != set(skill.capabilities):
                raise ValueError("CAPABILITY_DRIFT")
            if existing.status in ("REVOKED", "QUARANTINED"):
                raise ValueError(f"Skill status is {existing.status}")
                
        self.skills[skill.name] = RegisteredSkill(skill, identity, attestation)

    def revoke(self, skill_name: str):
        if skill_name in self.skills:
            self.skills[skill_name].status = "REVOKED"
            
    def quarantine(self, skill_name: str):
        if skill_name in self.skills:
            self.skills[skill_name].status = "QUARANTINED"

    def match_capabilities(self, candidate: str, required_capabilities: List[str]) -> CapabilityMatch:
        for name, registered in self.skills.items():
            if registered.status != "VERIFIED":
                continue
            skill = registered.skill
            if skill.available and all(req in skill.capabilities for req in required_capabilities):
                return CapabilityMatch(
                    candidate=candidate,
                    required_capabilities=required_capabilities,
                    matching_skill=name,
                    compatible=True,
                    missing_capabilities=[]
                )
                
        return CapabilityMatch(
            candidate=candidate,
            required_capabilities=required_capabilities,
            matching_skill=None,
            compatible=False,
            missing_capabilities=required_capabilities
        )
        
    def get_skill(self, skill_name: str) -> Optional[RegisteredSkill]:
        return self.skills.get(skill_name)
    def get_snapshot_hash(self) -> str:
        payloads = []
        for name, registered in sorted(self.skills.items()):
            if registered.status == "VERIFIED":
                payloads.append(f"{name}:{registered.identity.skill_version}:{registered.identity.implementation_hash}:{registered.attestation.attestation_hash}")
        return hashlib.sha256(";".join(payloads).encode()).hexdigest()

    def get_discovery_info(self) -> Dict[str, dict]:
        info = {}
        for name, registered in self.skills.items():
            if registered.status == "VERIFIED":
                info[name] = {
                    "version": registered.identity.skill_version,
                    "implementation_hash": registered.identity.implementation_hash,
                    "capabilities": registered.attestation.capabilities,
                    "attestation_hash": registered.attestation.attestation_hash
                }
        return info


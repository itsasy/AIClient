import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class SkillIdentity:
    skill_id: str
    skill_name: str
    skill_version: str
    implementation_hash: str
    manifest_hash: str
    declared_at: float = field(default_factory=time.time)

    def calculate_identity_hash(self) -> str:
        payload = f"{self.skill_id}:{self.skill_name}:{self.skill_version}:{self.implementation_hash}:{self.manifest_hash}"
        return hashlib.sha256(payload.encode()).hexdigest()

@dataclass
class CapabilityAttestation:
    skill_id: str
    skill_version: str
    implementation_hash: str
    capabilities: List[str]
    attestation_hash: str = ""

    def generate_attestation_hash(self) -> str:
        payload = {
            "skill_id": self.skill_id,
            "skill_version": self.skill_version,
            "implementation_hash": self.implementation_hash,
            "capabilities": sorted(self.capabilities)
        }
        self.attestation_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        return self.attestation_hash

    def verify(self) -> bool:
        expected = hashlib.sha256(json.dumps({
            "skill_id": self.skill_id,
            "skill_version": self.skill_version,
            "implementation_hash": self.implementation_hash,
            "capabilities": sorted(self.capabilities)
        }, sort_keys=True).encode()).hexdigest()
        return self.attestation_hash == expected

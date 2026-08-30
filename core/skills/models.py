from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class Skill:
    name: str
    location: str
    description: str
    capabilities: List[str] = field(default_factory=list)
    requirements: List[str] = field(default_factory=list)
    mutating: bool = False
    available: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "location": self.location,
            "description": self.description,
            "capabilities": self.capabilities,
            "requirements": self.requirements,
            "mutating": self.mutating,
            "available": self.available
        }

@dataclass
class CapabilityMatch:
    candidate: str
    required_capabilities: List[str]
    matching_skill: Optional[str]
    compatible: bool
    missing_capabilities: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate": self.candidate,
            "required_capabilities": self.required_capabilities,
            "matching_skill": self.matching_skill,
            "compatible": self.compatible,
            "missing_capabilities": self.missing_capabilities
        }

@dataclass
class ExecutionResult:
    skill: str
    candidate: str
    status: str  # SUCCESS, FAILED, ROLLED_BACK, REJECTED, BLOCKED
    actions: List[str] = field(default_factory=list)
    files_changed: List[str] = field(default_factory=list)
    tests: Dict[str, bool] = field(default_factory=dict)
    rollback: Dict[str, bool] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill": self.skill,
            "candidate": self.candidate,
            "status": self.status,
            "actions": self.actions,
            "files_changed": self.files_changed,
            "tests": self.tests,
            "rollback": self.rollback,
            "error": self.error
        }

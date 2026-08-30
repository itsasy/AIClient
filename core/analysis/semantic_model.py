from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import hashlib
import json

@dataclass
class SemanticLocation:
    file_path: str
    line_start: int

@dataclass
class SemanticUnknown:
    code: str
    explanation: str
    location: Optional[SemanticLocation] = None
    blocking: bool = False

@dataclass
class CompatibilityIssue:
    code: str
    severity: str # BLOCKING, WARNING, INFO
    explanation: str
    location: Optional[SemanticLocation] = None
    evidence: str = ""

@dataclass
class InterfaceCompatibility:
    source_class: str
    target_interface: str
    status: str # COMPATIBLE, PARTIALLY_COMPATIBLE, INCOMPATIBLE, UNKNOWN
    issues: List[CompatibilityIssue] = field(default_factory=list)

@dataclass
class SemanticReference:
    source: str
    target: str
    reference_type: str # IMPORT, CALL, INSTANTIATION, INHERITANCE, ATTRIBUTE, SYMBOL_REFERENCE, INTERFACE, UNKNOWN
    resolution_status: str # CONFIRMED, INFERRED, PARTIAL, UNKNOWN
    confidence: str
    location: Optional[SemanticLocation] = None
    evidence: str = ""

@dataclass
class SemanticDependency:
    source: str
    target: str
    dependency_type: str # IMPORT_DEPENDENCY, SYMBOL_DEPENDENCY, INHERITANCE_DEPENDENCY, REFERENCE_DEPENDENCY, INTERFACE_DEPENDENCY, UNKNOWN_DEPENDENCY
    resolution_status: str # CONFIRMED, INFERRED, PARTIAL, UNKNOWN
    confidence: str
    evidence: str = ""

@dataclass
class ResolutionResult:
    status: str
    resolved_target: str
    confidence: str
    evidence: str

@dataclass
class DependencyImpact:
    symbol: str
    direct_consumers: List[str] = field(default_factory=list)
    indirect_consumers: List[str] = field(default_factory=list)
    importers: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    subclasses: List[str] = field(default_factory=list)
    implementations: List[str] = field(default_factory=list)
    dependent_modules: List[str] = field(default_factory=list)
    affected_interfaces: List[str] = field(default_factory=list)
    unknown_consumers: List[str] = field(default_factory=list)

@dataclass
class SemanticSymbolModel:
    name: str
    symbol_type: str
    module: str
    resolved_dependencies: List[SemanticDependency] = field(default_factory=list)
    impact: Optional[DependencyImpact] = None

@dataclass
class SemanticModuleModel:
    name: str
    path: str
    imports: List[SemanticReference] = field(default_factory=list)
    symbols: Dict[str, SemanticSymbolModel] = field(default_factory=dict)

@dataclass
class SemanticProgramModel:
    source_identity: str
    source_manifest_hash: str
    analysis_hash: str
    modules: Dict[str, SemanticModuleModel] = field(default_factory=dict)
    symbols: Dict[str, SemanticSymbolModel] = field(default_factory=dict)
    references: List[SemanticReference] = field(default_factory=list)
    dependencies: List[SemanticDependency] = field(default_factory=list)
    interfaces: List[InterfaceCompatibility] = field(default_factory=list)
    compatibilities: List[InterfaceCompatibility] = field(default_factory=list)
    impacts: Dict[str, DependencyImpact] = field(default_factory=dict)
    issues: List[CompatibilityIssue] = field(default_factory=list)
    unknowns: List[SemanticUnknown] = field(default_factory=list)
    semantic_analysis_hash: str = ""
    analyzer_version: str = "1.0.0"

    def generate_hash(self) -> str:
        payload = {
            "analysis_hash": self.analysis_hash,
            "source_identity": self.source_identity,
            "analyzer_version": self.analyzer_version,
            "modules": sorted(self.modules.keys()),
            "dependencies": sorted([f"{d.source}->{d.target}:{d.dependency_type}:{d.resolution_status}" for d in self.dependencies]),
            "interfaces": sorted([f"{i.source_class}->{i.target_interface}:{i.status}" for i in self.interfaces]),
            "unknowns": sorted([f"{u.code}:{u.blocking}" for u in self.unknowns])
        }
        self.semantic_analysis_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        return self.semantic_analysis_hash

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import hashlib
import json

@dataclass
class StructuralLocation:
    file_path: str
    line_start: int
    line_end: int
    col_offset: int

@dataclass
class StructuralIssue:
    issue_type: str
    description: str
    classification: str # BLOCKING, WARNING, INFO
    location: Optional[StructuralLocation] = None

@dataclass
class Unknown:
    code: str
    explanation: str
    location: Optional[StructuralLocation] = None
    impact: str = ""
    blocking: bool = False

@dataclass
class ImportModel:
    source_module: str
    target_module: str
    imported_symbols: List[str]
    alias: Optional[str]
    import_type: str # "import" or "from"
    resolution_status: str # "RESOLVED", "UNRESOLVED", "UNKNOWN"
    location: Optional[StructuralLocation] = None

@dataclass
class ReferenceModel:
    source: str
    target: str
    resolution_status: str # "CONFIRMED", "INFERRED", "UNKNOWN"
    location: Optional[StructuralLocation] = None

@dataclass
class DependencyModel:
    source_module: str
    target_module: str
    dependency_type: str # "INTERNAL" or "EXTERNAL" or "UNKNOWN"

@dataclass
class InterfaceModel:
    name: str
    confidence: str # "EXPLICIT", "INFERRED"
    location: Optional[StructuralLocation] = None

@dataclass
class SymbolModel:
    name: str
    symbol_type: str # "class", "function", "method", "constant"
    module: str
    parent_symbol: Optional[str]
    visibility: str # "public", "private"
    signature: str = ""
    location: Optional[StructuralLocation] = None

@dataclass
class ClassModel(SymbolModel):
    bases: List[str] = field(default_factory=list)
    methods: List[str] = field(default_factory=list)
    attributes: List[str] = field(default_factory=list)

@dataclass
class FunctionModel(SymbolModel):
    parameters: List[str] = field(default_factory=list)
    return_annotation: str = ""
    calls: List[str] = field(default_factory=list)

@dataclass
class ModuleModel:
    name: str
    path: str
    package: str
    symbols: Dict[str, SymbolModel] = field(default_factory=dict)
    imports: List[ImportModel] = field(default_factory=list)

@dataclass
class ProjectStructuralModel:
    project_identity: str
    project_root_identity: str
    scope: Dict[str, Any] = field(default_factory=dict)
    modules: Dict[str, ModuleModel] = field(default_factory=dict)
    references: List[ReferenceModel] = field(default_factory=list)
    dependencies: List[DependencyModel] = field(default_factory=list)
    interfaces: List[InterfaceModel] = field(default_factory=list)
    issues: List[StructuralIssue] = field(default_factory=list)
    unknowns: List[Unknown] = field(default_factory=list)
    source_manifest_hash: str = ""
    analysis_hash: str = ""
    analyzer_version: str = "1.0.0"

    def generate_hash(self) -> str:
        payload = {
            "source_manifest_hash": self.source_manifest_hash,
            "project_identity": self.project_identity,
            "project_root_identity": self.project_root_identity,
            "analyzer_version": self.analyzer_version,
            "scope": self.scope,
            "modules": sorted(self.modules.keys()),
            "dependencies": sorted([f"{d.source_module}->{d.target_module}:{d.dependency_type}" for d in self.dependencies]),
            "issues": sorted([f"{i.issue_type}:{i.classification}" for i in self.issues]),
            "unknowns": sorted([f"{u.code}:{u.blocking}" for u in self.unknowns])
        }
        self.analysis_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        return self.analysis_hash

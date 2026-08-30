import re
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, List, Dict, Set
from core.discovery.environment import ProjectEnvironment
from core.discovery.understanding import ProjectUnderstanding, Bottleneck

@dataclass
class ModuleBoundary:
    name: str
    path: str
    files: List[str] = field(default_factory=list)
    internal_dependencies: List[str] = field(default_factory=list)
    framework_dependencies: List[str] = field(default_factory=list)
    infrastructure_dependencies: List[str] = field(default_factory=list)
    external_dependencies: List[str] = field(default_factory=list)
    ui_dependencies: List[str] = field(default_factory=list)
    vertical_dependencies: List[str] = field(default_factory=list)
    coupling_score: int = 0
    evidence: List[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "files": self.files,
            "internal_dependencies": self.internal_dependencies,
            "framework_dependencies": self.framework_dependencies,
            "infrastructure_dependencies": self.infrastructure_dependencies,
            "external_dependencies": self.external_dependencies,
            "ui_dependencies": self.ui_dependencies,
            "vertical_dependencies": self.vertical_dependencies,
            "coupling_score": self.coupling_score,
            "evidence": self.evidence
        }

@dataclass
class ReuseCandidate:
    module: str
    classification: str
    reasons: List[str] = field(default_factory=list)
    adaptation_points: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "module": self.module,
            "classification": self.classification,
            "reasons": self.reasons,
            "adaptation_points": self.adaptation_points
        }

@dataclass
class AnalysisResult:
    boundaries: List[ModuleBoundary] = field(default_factory=list)
    reuse_analysis: List[ReuseCandidate] = field(default_factory=list)
    new_bottlenecks: List[Bottleneck] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundaries": [b.to_dict() for b in self.boundaries],
            "reuse_analysis": [r.to_dict() for r in self.reuse_analysis],
            "new_bottlenecks": [b.__dict__ for b in self.new_bottlenecks]
        }

class AnalysisEngine:
    FRAMEWORK_KEYWORDS = {"flask", "django", "fastapi", "express", "react", "vue", "laravel", "spring", "angular"}
    INFRA_KEYWORDS = {"sqlalchemy", "sqlite", "sqlite3", "psycopg2", "redis", "mysql", "mongodb", "boto3", "requests", "axios", "fs", "path", "http", "socket", "db", "database"}
    UI_KEYWORDS = {"ui", "views", "components", "templates", "html", "css"}
    
    def __init__(self, root: str | Path, env: ProjectEnvironment, understanding: ProjectUnderstanding):
        self.root = Path(root).expanduser().resolve()
        self.env = env
        self.understanding = understanding
        self.result = AnalysisResult()
        
        self.module_names = {m["name"] for m in self.understanding.modules}
        self.vertical_keywords = {"clinical", "restaurant", "odontogram", "dental", "patients", "medical"}

    def analyze(self) -> AnalysisResult:
        self._analyze_boundaries()
        self._detect_circular_dependencies()
        self._analyze_reuse()
        return self.result

    def _analyze_boundaries(self):
        for mod in self.understanding.modules:
            boundary = ModuleBoundary(name=mod["name"], path=mod["path"])
            mod_path = self.root / mod["path"]
            
            if not mod_path.is_dir():
                continue
                
            for root_dir, _, files in os.walk(mod_path):
                for f in files:
                    if f.endswith((".py", ".js", ".ts", ".php")):
                        rel_file = Path(root_dir) / f
                        try:
                            boundary.files.append(str(rel_file.relative_to(mod_path)).replace(os.sep, '/'))
                            content = rel_file.read_text(encoding="utf-8", errors="ignore")
                            self._extract_dependencies(content, boundary, str(rel_file.relative_to(self.root)).replace(os.sep, '/'))
                        except Exception:
                            pass
                            
            # Deduplicate
            boundary.internal_dependencies = list(set(boundary.internal_dependencies))
            boundary.framework_dependencies = list(set(boundary.framework_dependencies))
            boundary.infrastructure_dependencies = list(set(boundary.infrastructure_dependencies))
            boundary.external_dependencies = list(set(boundary.external_dependencies))
            boundary.ui_dependencies = list(set(boundary.ui_dependencies))
            boundary.vertical_dependencies = list(set(boundary.vertical_dependencies))
            
            # Calculate coupling score (heuristic)
            boundary.coupling_score = (
                len(boundary.internal_dependencies) * 2 +
                len(boundary.infrastructure_dependencies) * 3 +
                len(boundary.framework_dependencies) * 1 +
                len(boundary.vertical_dependencies) * 4
            )
            
            self.result.boundaries.append(boundary)
            
    def _extract_dependencies(self, content: str, boundary: ModuleBoundary, file_path: str):
        # Very naive import extraction for multiple languages
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            tokens = re.split(r'\s+|[;\'\"(){},.]', line)
            tokens = [t.lower() for t in tokens if t]
            
            is_import = False
            if "import" in tokens or "require" in tokens or "use" in tokens or "from" in tokens:
                is_import = True
                
            if is_import:
                for token in tokens:
                    if token in ("import", "from", "require", "use", "const", "let", "var", "as"):
                        continue
                        
                    # Frameworks
                    if token in self.FRAMEWORK_KEYWORDS:
                        boundary.framework_dependencies.append(token)
                        boundary.evidence.append(f"Framework dependency {token} in {file_path}")
                        
                    # Infrastructure
                    elif token in self.INFRA_KEYWORDS:
                        boundary.infrastructure_dependencies.append(token)
                        boundary.evidence.append(f"Infra dependency {token} in {file_path}")
                        
                    # Internal modules
                    elif token in self.module_names and token != boundary.name.lower():
                        boundary.internal_dependencies.append(token)
                        boundary.evidence.append(f"Internal dependency {token} in {file_path}")
                        
                    # UI
                    elif token in self.UI_KEYWORDS:
                        boundary.ui_dependencies.append(token)
                        boundary.evidence.append(f"UI dependency {token} in {file_path}")
                        
                    # Vertical specific
                    elif token in self.vertical_keywords:
                        boundary.vertical_dependencies.append(token)
                        boundary.evidence.append(f"Vertical dependency {token} in {file_path}")

    def _detect_circular_dependencies(self):
        # Naive circular dependency detection
        for b1 in self.result.boundaries:
            for b2_name in b1.internal_dependencies:
                b2 = next((b for b in self.result.boundaries if b.name.lower() == b2_name.lower()), None)
                if b2 and b1.name.lower() in b2.internal_dependencies:
                    self.result.new_bottlenecks.append(Bottleneck(
                        type="circular_dependency",
                        severity="high",
                        description=f"Circular dependency detected between {b1.name} and {b2.name}",
                        evidence=[b1.path, b2.path],
                        confidence="medium"
                    ))
                    
        # Check for heavy infra or framework coupling
        for b in self.result.boundaries:
            if len(b.infrastructure_dependencies) >= 3:
                self.result.new_bottlenecks.append(Bottleneck(
                    type="infrastructure_leakage",
                    severity="medium",
                    description=f"Module {b.name} has heavy infrastructure dependencies ({', '.join(b.infrastructure_dependencies)})",
                    evidence=[b.path],
                    confidence="high"
                ))
            if len(b.framework_dependencies) >= 2:
                self.result.new_bottlenecks.append(Bottleneck(
                    type="framework_leakage",
                    severity="medium",
                    description=f"Module {b.name} has multiple framework dependencies",
                    evidence=[b.path],
                    confidence="high"
                ))
            if b.coupling_score > 15:
                self.result.new_bottlenecks.append(Bottleneck(
                    type="high_coupling",
                    severity="high",
                    description=f"Module {b.name} has a high coupling score ({b.coupling_score})",
                    evidence=[b.path],
                    confidence="medium"
                ))

    def _analyze_reuse(self):
        for b in self.result.boundaries:
            reasons = []
            adaptation_points = []
            classification = "UNKNOWN"
            
            if b.vertical_dependencies:
                classification = "VERTICAL_SPECIFIC"
                reasons.append(f"Depends on vertical-specific modules: {', '.join(b.vertical_dependencies)}")
            elif b.coupling_score > 15:
                classification = "HIGHLY_COUPLED"
                reasons.append(f"High coupling score ({b.coupling_score})")
            elif b.infrastructure_dependencies or b.framework_dependencies:
                classification = "REUSABLE_WITH_ADAPTATION"
                reasons.append("Has some infrastructure or framework coupling")
                if b.infrastructure_dependencies:
                    adaptation_points.append(f"Infrastructure adapters for: {', '.join(b.infrastructure_dependencies)}")
                if b.framework_dependencies:
                    adaptation_points.append(f"Framework adapters for: {', '.join(b.framework_dependencies)}")
            elif not b.internal_dependencies and len(b.files) > 0:
                classification = "REUSABLE"
                reasons.append("Isolated boundary with no external dependencies")
            elif len(b.files) == 0:
                classification = "UNKNOWN"
                reasons.append("No files detected in module")
            else:
                classification = "REUSABLE"
                reasons.append("Low coupling, clear boundary")
                
            self.result.reuse_analysis.append(ReuseCandidate(
                module=b.name,
                classification=classification,
                reasons=reasons,
                adaptation_points=adaptation_points
            ))

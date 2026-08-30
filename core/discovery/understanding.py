import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, List, Dict
from core.discovery.environment import ProjectEnvironment, DiscoveryEvidence

@dataclass
class Bottleneck:
    type: str
    severity: str
    description: str
    evidence: List[str]
    confidence: str

@dataclass
class ProjectUnderstanding:
    architecture: str = "unknown"
    directories: List[Dict[str, Any]] = field(default_factory=list)
    modules: List[Dict[str, Any]] = field(default_factory=list)
    entrypoints: List[Dict[str, Any]] = field(default_factory=list)
    configuration: List[Dict[str, Any]] = field(default_factory=list)
    dependencies: List[Dict[str, Any]] = field(default_factory=list)
    api_surface: List[Dict[str, Any]] = field(default_factory=list)
    frontend_surface: List[Dict[str, Any]] = field(default_factory=list)
    test_surface: List[Dict[str, Any]] = field(default_factory=list)
    build_surface: List[Dict[str, Any]] = field(default_factory=list)
    integration_points: List[Dict[str, Any]] = field(default_factory=list)
    reuse_candidates: List[Dict[str, Any]] = field(default_factory=list)
    bottlenecks: List[Bottleneck] = field(default_factory=list)
    unknowns: List[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "architecture": self.architecture,
            "directories": self.directories,
            "modules": self.modules,
            "entrypoints": self.entrypoints,
            "configuration": self.configuration,
            "dependencies": self.dependencies,
            "api_surface": self.api_surface,
            "frontend_surface": self.frontend_surface,
            "test_surface": self.test_surface,
            "build_surface": self.build_surface,
            "integration_points": self.integration_points,
            "reuse_candidates": self.reuse_candidates,
            "bottlenecks": [b.__dict__ for b in self.bottlenecks],
            "unknowns": self.unknowns
        }

class UnderstandingEngine:
    EXCLUDED_DIRS = {
        ".git", ".venv", "venv", "__pycache__", ".pytest_cache", "node_modules", "vendor",
        "dist", "build", "out", ".next", "target", ".idea", ".vscode", "storage"
    }
    
    def __init__(self, root: str | Path, env: ProjectEnvironment):
        self.root = Path(root).expanduser().resolve()
        self.env = env
        self.understanding = ProjectUnderstanding()

    def analyze(self) -> ProjectUnderstanding:
        self._analyze_filesystem()
        self._detect_architecture()
        self._detect_bottlenecks()
        return self.understanding

    def _analyze_filesystem(self):
        """Walks the filesystem once to collect all structural evidence."""
        # Using a deterministic traversal
        for root, dirs, files in os.walk(self.root):
            dirs[:] = [d for d in dirs if d not in self.EXCLUDED_DIRS]
            rel_root = Path(root).relative_to(self.root)
            
            # Record directories
            if str(rel_root) != ".":
                self.understanding.directories.append({
                    "path": str(rel_root).replace(os.sep, '/'),
                    "evidence": "filesystem"
                })
                
            self._analyze_directory(rel_root, dirs, files)

    def _analyze_directory(self, rel_root: Path, dirs: List[str], files: List[str]):
        str_root = str(rel_root).replace(os.sep, '/')
        
        # Modules / Features
        if str_root in ("modules", "features", "src/features", "adapters", "app", "src"):
            for d in dirs:
                mod_path = f"{str_root}/{d}"
                if str_root in ("modules", "features", "src/features", "adapters") or d in ("Models", "Services", "Http", "Console"):
                    self.understanding.modules.append({
                        "name": d,
                        "path": mod_path,
                        "type": "module" if str_root in ("modules", "features") else "component",
                        "evidence": ["filesystem"]
                    })
                    
                    # Automatically flag as reuse candidate if self-contained (rough heuristic)
                    self.understanding.reuse_candidates.append({
                        "candidate": mod_path,
                        "reason": ["Self-contained directory within structural boundary"],
                        "confidence": "medium"
                    })
                
        # API Surface
        if "api" in str_root.split('/') or "routes" in str_root.split('/') or "controllers" in str_root.split('/') or "Http" in str_root.split('/'):
            self.understanding.api_surface.append({
                "path": str_root,
                "evidence": ["directory name implies API surface"]
            })
            
        # Frontend Surface
        if "ui" in str_root.split('/') or "frontend" in str_root.split('/') or "components" in str_root.split('/') or "views" in str_root.split('/') or "pages" in str_root.split('/'):
            self.understanding.frontend_surface.append({
                "path": str_root,
                "evidence": ["directory name implies frontend UI"]
            })
            
        # Test Surface
        if "test" in str_root.split('/') or "tests" in str_root.split('/'):
            self.understanding.test_surface.append({
                "path": str_root,
                "evidence": ["directory name implies tests"]
            })
            
        # Files Analysis
        for f in files:
            file_path = f"{str_root}/{f}" if str_root != "." else f
            
            # Entrypoints
            if f in ("app.py", "main.py", "wsgi.py", "manage.py", "index.js", "main.js", "artisan", "AndroidManifest.xml") or (str_root == "public" and f == "index.php"):
                self.understanding.entrypoints.append({
                    "path": file_path,
                    "evidence": ["well-known entrypoint name"]
                })
                
            # Configuration
            if f.startswith("config.") or f.startswith("settings.") or f.endswith("config.json") or f.endswith("config.js") or f.endswith("config.ts") or f in ("pyproject.toml", "package.json", "composer.json", "build.gradle", "application.yml"):
                self.understanding.configuration.append({
                    "path": file_path,
                    "evidence": ["configuration file naming convention"]
                })
                
            # Secrets / Sensitive
            if f.startswith(".env") or f.endswith(".pem") or "secret" in f.lower() or "credential" in f.lower():
                self.understanding.configuration.append({
                    "path": file_path,
                    "type": "secret-bearing-file",
                    "evidence": ["sensitive file name pattern"]
                })
                
            # Integration points (Adapters)
            if "adapter" in f.lower() or "client" in f.lower() or "provider" in f.lower():
                self.understanding.integration_points.append({
                    "path": file_path,
                    "evidence": ["filename implies external integration"]
                })
                
    def _detect_architecture(self):
        # Infer architecture from evidence
        apis = len(self.understanding.api_surface) > 0
        frontends = len(self.understanding.frontend_surface) > 0
        
        if apis and frontends:
            self.understanding.architecture = "Fullstack (API + Frontend detected)"
        elif apis:
            self.understanding.architecture = "Backend / API-heavy"
        elif frontends:
            self.understanding.architecture = "Frontend-heavy"
        else:
            self.understanding.architecture = "partially_known"

    def _detect_bottlenecks(self):
        # 1. Project Bottlenecks (e.g., missing tests for important modules)
        for mod in self.understanding.modules:
            # Try to see if this module has tests inside it
            mod_path = mod["path"]
            has_tests = False
            # Check if there is a test surface matching this module
            for ts in self.understanding.test_surface:
                if mod["name"] in ts["path"] or ts["path"].startswith(mod_path):
                    has_tests = True
                    break
            
            # We don't have a full AST so we just guess:
            # If the project has modules but no global tests directory either
            if not has_tests and len(self.understanding.test_surface) == 0:
                self.understanding.bottlenecks.append(Bottleneck(
                    type="missing_tests",
                    severity="high",
                    description=f"Module '{mod['name']}' has no evident tests and no global test surface was found.",
                    evidence=[mod_path],
                    confidence="medium"
                ))
                
        # 2. AIClient Bottlenecks (e.g., hardcoded pytest in workflows)
        # We can dynamically check AIClient's core if we are analyzing AIClient itself.
        # But wait, Project Understanding analyzes the TARGET, not AIClient (unless TARGET == AIClient).
        # We look for hardcoded workflows in the target.
        if (self.root / "core" / "workflows").exists():
            # Looks like an orchestrator or similar pattern
            import re
            for w_root, w_dirs, w_files in os.walk(self.root / "core" / "workflows"):
                for w_file in w_files:
                    if w_file.endswith(".py"):
                        content = (Path(w_root) / w_file).read_text(encoding="utf-8", errors="ignore")
                        # Looking for naive hardcodings
                        if "pytest" in content and "DiscoveryEngine" not in content and "test.py" not in w_file:
                            self.understanding.bottlenecks.append(Bottleneck(
                                type="hardcoded_tool",
                                severity="high",
                                description=f"Generic workflow {w_file} might assume pytest",
                                evidence=[f"core/workflows/{w_file}"],
                                confidence="low"
                            ))
                            
        # Look for giant files
        for root_dir, dirs, files in os.walk(self.root):
            dirs[:] = [d for d in dirs if d not in self.EXCLUDED_DIRS]
            for f in files:
                if f.endswith((".py", ".js", ".php", ".ts", ".java")):
                    full_path = Path(root_dir) / f
                    try:
                        size = full_path.stat().st_size
                        if size > 150000: # ~150KB code file is usually very large
                            self.understanding.bottlenecks.append(Bottleneck(
                                type="large_file",
                                severity="medium",
                                description=f"File {f} is unusually large and might be overly coupled.",
                                evidence=[str(full_path.relative_to(self.root)).replace(os.sep, '/')],
                                confidence="high"
                            ))
                    except Exception:
                        pass
                        
        if not self.understanding.bottlenecks:
            self.understanding.bottlenecks = []

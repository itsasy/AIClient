from dataclasses import dataclass, field
from typing import Any, Optional

@dataclass
class DiscoveryEvidence:
    value: str
    source: str
    confidence: str # 'high', 'medium', 'low'

@dataclass
class ProjectEnvironment:
    root: str = ""
    languages: dict[str, DiscoveryEvidence] = field(default_factory=dict)
    frameworks: dict[str, DiscoveryEvidence] = field(default_factory=dict)
    runtimes: dict[str, DiscoveryEvidence] = field(default_factory=dict)
    package_managers: dict[str, DiscoveryEvidence] = field(default_factory=dict)
    
    backend: Optional[DiscoveryEvidence] = None
    frontend: Optional[DiscoveryEvidence] = None
    database: Optional[DiscoveryEvidence] = None
    
    test_runner: Optional[list[DiscoveryEvidence]] = None
    build_system: Optional[list[DiscoveryEvidence]] = None
    lint_tools: dict[str, DiscoveryEvidence] = field(default_factory=dict)
    formatter: Optional[list[DiscoveryEvidence]] = None
    
    detected_modules: list[dict[str, Any]] = field(default_factory=list)
    important_files: list[str] = field(default_factory=list)
    important_directories: list[dict[str, Any]] = field(default_factory=list)
    
    # Store candidates for each command category (test, build, lint, format, dev, start)
    commands: dict[str, list[DiscoveryEvidence]] = field(default_factory=lambda: {
        "test": [], "build": [], "lint": [], "format": [], "dev": [], "start": []
    })
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "root": self.root,
            "languages": {k: v.__dict__ for k, v in self.languages.items()},
            "frameworks": {k: v.__dict__ for k, v in self.frameworks.items()},
            "runtimes": {k: v.__dict__ for k, v in self.runtimes.items()},
            "package_managers": {k: v.__dict__ for k, v in self.package_managers.items()},
            "backend": self.backend.__dict__ if self.backend else "unknown",
            "frontend": self.frontend.__dict__ if self.frontend else "unknown",
            "database": self.database.__dict__ if self.database else "unknown",
            "test_runner": [t.__dict__ for t in self.test_runner] if self.test_runner else "unknown",
            "build_system": [b.__dict__ for b in self.build_system] if self.build_system else "unknown",
            "lint_tools": {k: v.__dict__ for k, v in self.lint_tools.items()},
            "formatter": [f.__dict__ for f in self.formatter] if self.formatter else "unknown",
            "detected_modules": self.detected_modules,
            "important_files": self.important_files,
            "important_directories": self.important_directories,
            "commands": {k: [cmd.__dict__ for cmd in v] for k, v in self.commands.items()},
        }

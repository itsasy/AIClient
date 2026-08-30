import ast
from pathlib import Path
from typing import List, Dict, Optional, Any
import hashlib
from core.analysis.structural_model import (
    ProjectStructuralModel,
    ModuleModel,
    SymbolModel,
    ClassModel,
    FunctionModel,
    ImportModel,
    ReferenceModel,
    DependencyModel,
    InterfaceModel,
    StructuralLocation,
    StructuralIssue,
    Unknown
)

class ProjectAnalysisRequest:
    def __init__(self, root: str, include_patterns: List[str] = None, exclude_patterns: List[str] = None, candidate_modules: List[str] = None):
        self.root = Path(root)
        self.include_patterns = include_patterns or ["**/*.py"]
        self.exclude_patterns = exclude_patterns or []
        self.candidate_modules = candidate_modules or []

class ProjectStructuralAnalyzer:
    def __init__(self, request: ProjectAnalysisRequest):
        self.request = request
        self.model = ProjectStructuralModel(
            project_identity=self.request.root.name,
            project_root_identity=str(self.request.root),
            scope={
                "include": self.request.include_patterns,
                "exclude": self.request.exclude_patterns,
                "candidates": self.request.candidate_modules
            }
        )

    def is_in_scope(self, path: Path) -> bool:
        try:
            path.relative_to(self.request.root)
        except ValueError:
            return False
            
        if not path.suffix == ".py":
            return False
            
        # Simplified boundary check for read-only AST
        return True

    def analyze(self) -> ProjectStructuralModel:
        manifest_payload = ""
        for py_file in self.request.root.rglob("*.py"):
            if not self.is_in_scope(py_file):
                continue
                
            try:
                content = py_file.read_text(encoding="utf-8")
                manifest_payload += f"{py_file.relative_to(self.request.root)}:{hashlib.sha256(content.encode()).hexdigest()}\n"
                self._analyze_file(py_file, content)
            except Exception as e:
                self.model.issues.append(StructuralIssue(
                    issue_type="parse_error",
                    description=str(e),
                    classification="WARNING",
                    location=StructuralLocation(str(py_file), 0, 0, 0)
                ))

        self.model.source_manifest_hash = hashlib.sha256(manifest_payload.encode()).hexdigest()
        
        self._build_dependencies()
        self.model.generate_hash()
        
        return self.model

    def _get_module_name(self, py_file: Path) -> str:
        rel = py_file.relative_to(self.request.root)
        if rel.name == "__init__.py":
            return ".".join(rel.parent.parts)
        return ".".join(rel.with_suffix("").parts)

    def _analyze_file(self, py_file: Path, content: str):
        module_name = self._get_module_name(py_file)
        if not module_name:
            module_name = "__main__"
            
        module_model = ModuleModel(
            name=module_name,
            path=str(py_file),
            package=".".join(module_name.split(".")[:-1])
        )
        self.model.modules[module_name] = module_model

        try:
            tree = ast.parse(content, filename=str(py_file))
        except SyntaxError as e:
            self.model.issues.append(StructuralIssue("syntax_error", str(e), "BLOCKING", StructuralLocation(str(py_file), e.lineno or 0, e.lineno or 0, e.offset or 0)))
            return

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_model.imports.append(ImportModel(
                        source_module=module_name,
                        target_module=alias.name,
                        imported_symbols=[],
                        alias=alias.asname,
                        import_type="import",
                        resolution_status="UNKNOWN",
                        location=StructuralLocation(str(py_file), getattr(node, 'lineno', 0), getattr(node, 'end_lineno', 0), getattr(node, 'col_offset', 0))
                    ))
            elif isinstance(node, ast.ImportFrom):
                target = node.module if node.module else ""
                if node.level > 0:
                    parts = module_name.split(".")
                    target = ".".join(parts[:-node.level] + ([node.module] if node.module else []))
                
                module_model.imports.append(ImportModel(
                    source_module=module_name,
                    target_module=target,
                    imported_symbols=[alias.name for alias in node.names],
                    alias=None,
                    import_type="from",
                    resolution_status="UNKNOWN",
                    location=StructuralLocation(str(py_file), getattr(node, 'lineno', 0), getattr(node, 'end_lineno', 0), getattr(node, 'col_offset', 0))
                ))
            elif isinstance(node, ast.ClassDef):
                cmodel = ClassModel(
                    name=node.name,
                    symbol_type="class",
                    module=module_name,
                    parent_symbol=None,
                    visibility="public" if not node.name.startswith("_") else "private",
                    location=StructuralLocation(str(py_file), getattr(node, 'lineno', 0), getattr(node, 'end_lineno', 0), getattr(node, 'col_offset', 0))
                )
                module_model.symbols[node.name] = cmodel
                
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id in ["ABC", "Protocol"]:
                        self.model.interfaces.append(InterfaceModel(
                            name=f"{module_name}.{node.name}",
                            confidence="EXPLICIT",
                            location=cmodel.location
                        ))

                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        cmodel.methods.append(item.name)
                        module_model.symbols[f"{node.name}.{item.name}"] = FunctionModel(
                            name=item.name,
                            symbol_type="method",
                            module=module_name,
                            parent_symbol=node.name,
                            visibility="public" if not item.name.startswith("_") else "private",
                            location=StructuralLocation(str(py_file), getattr(item, 'lineno', 0), getattr(item, 'end_lineno', 0), getattr(item, 'col_offset', 0))
                        )
            elif isinstance(node, ast.FunctionDef):
                module_model.symbols[node.name] = FunctionModel(
                    name=node.name,
                    symbol_type="function",
                    module=module_name,
                    parent_symbol=None,
                    visibility="public" if not node.name.startswith("_") else "private",
                    location=StructuralLocation(str(py_file), getattr(node, 'lineno', 0), getattr(node, 'end_lineno', 0), getattr(node, 'col_offset', 0))
                )
                
    def _build_dependencies(self):
        root_names = {m.split(".")[0] for m in self.model.modules.keys()}
        for mod_name, mod in self.model.modules.items():
            for imp in mod.imports:
                target = imp.target_module
                dep_type = "EXTERNAL"
                if target.split(".")[0] in root_names or target in self.model.modules:
                    dep_type = "INTERNAL"
                    
                self.model.dependencies.append(DependencyModel(
                    source_module=mod_name,
                    target_module=target,
                    dependency_type=dep_type
                ))


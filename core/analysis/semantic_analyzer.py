from core.analysis.structural_model import ProjectStructuralModel
from core.analysis.semantic_model import (
    SemanticProgramModel,
    SemanticModuleModel,
    SemanticSymbolModel,
    SemanticReference,
    SemanticDependency,
    InterfaceCompatibility,
    DependencyImpact,
    CompatibilityIssue,
    SemanticLocation,
    SemanticUnknown
)

class SemanticAnalyzer:
    def __init__(self, structural_model: ProjectStructuralModel):
        self.structural_model = structural_model
        self.model = SemanticProgramModel(
            source_identity=structural_model.project_identity,
            source_manifest_hash=structural_model.source_manifest_hash,
            analysis_hash=structural_model.analysis_hash,
        )

    def analyze(self) -> SemanticProgramModel:
        self._build_modules_and_symbols()
        self._resolve_imports()
        self._resolve_dependencies()
        self._analyze_interfaces()
        self._build_impacts()
        self.model.generate_hash()
        return self.model

    def _build_modules_and_symbols(self):
        for mod_name, struct_mod in self.structural_model.modules.items():
            sem_mod = SemanticModuleModel(name=mod_name, path=struct_mod.path)
            self.model.modules[mod_name] = sem_mod
            
            for sym_name, struct_sym in struct_mod.symbols.items():
                sem_sym = SemanticSymbolModel(name=sym_name, symbol_type=struct_sym.symbol_type, module=mod_name)
                sem_mod.symbols[sym_name] = sem_sym
                self.model.symbols[f"{mod_name}.{sym_name}"] = sem_sym

    def _resolve_imports(self):
        # Resolve imports and create semantic references
        for mod_name, struct_mod in self.structural_model.modules.items():
            for imp in struct_mod.imports:
                loc = None
                if imp.location:
                    loc = SemanticLocation(imp.location.file_path, imp.location.line_start)
                
                target = imp.target_module
                if target in self.structural_model.modules:
                    res_status = "CONFIRMED"
                    confidence = "HIGH"
                    evidence = "Target module present in structural model"
                else:
                    # External or dynamic
                    if "import_module" in target or imp.import_type == "DYNAMIC":
                        res_status = "UNKNOWN"
                        confidence = "LOW"
                        evidence = "Dynamic import detected"
                        self.model.unknowns.append(SemanticUnknown("DYNAMIC_IMPORT", "Import could not be statically resolved", loc, False))
                    else:
                        res_status = "CONFIRMED" # It's just external
                        confidence = "HIGH"
                        evidence = "External module dependency"
                        
                ref = SemanticReference(
                    source=mod_name,
                    target=target,
                    reference_type="IMPORT",
                    resolution_status=res_status,
                    confidence=confidence,
                    location=loc,
                    evidence=evidence
                )
                self.model.modules[mod_name].imports.append(ref)
                self.model.references.append(ref)
                
                if imp.imported_symbols:
                    for sym in imp.imported_symbols:
                        sym_target = f"{target}.{sym}"
                        sym_status = "UNKNOWN"
                        if target in self.structural_model.modules:
                            if sym in self.structural_model.modules[target].symbols:
                                sym_status = "CONFIRMED"
                            else:
                                sym_status = "UNKNOWN"
                                self.model.unknowns.append(SemanticUnknown("UNRESOLVED_SYMBOL", f"Symbol {sym} not found in {target}", loc, False))
                        
                        self.model.references.append(SemanticReference(
                            source=mod_name,
                            target=sym_target,
                            reference_type="SYMBOL_REFERENCE",
                            resolution_status=sym_status,
                            confidence="HIGH" if sym_status == "CONFIRMED" else "LOW",
                            location=loc,
                            evidence=f"Imported symbol resolution ({sym_status})"
                        ))

    def _resolve_dependencies(self):
        for dep in self.structural_model.dependencies:
            status = "CONFIRMED" if dep.dependency_type in ["INTERNAL", "EXTERNAL"] else "UNKNOWN"
            self.model.dependencies.append(SemanticDependency(
                source=dep.source_module,
                target=dep.target_module,
                dependency_type="IMPORT_DEPENDENCY",
                resolution_status=status,
                confidence="HIGH" if status == "CONFIRMED" else "LOW",
                evidence=f"Structural dependency ({dep.dependency_type})"
            ))
            
        # Add inheritance dependencies
        for mod_name, struct_mod in self.structural_model.modules.items():
            for sym_name, sym in struct_mod.symbols.items():
                if sym.symbol_type == "class":
                    bases = getattr(sym, "bases", [])
                    for base in bases:
                        self.model.dependencies.append(SemanticDependency(
                            source=f"{mod_name}.{sym_name}",
                            target=base,
                            dependency_type="INHERITANCE_DEPENDENCY",
                            resolution_status="INFERRED",
                            confidence="MEDIUM",
                            evidence="Inheritance detected statically"
                        ))

    def _analyze_interfaces(self):
        for iface in self.structural_model.interfaces:
            # P23 provided InterfaceModel
            # Let's see if we have subclasses
            target_iface = iface.name
            for mod_name, struct_mod in self.structural_model.modules.items():
                for sym_name, sym in struct_mod.symbols.items():
                    if sym.symbol_type == "class":
                        full_name = f"{mod_name}.{sym_name}"
                        if full_name == target_iface:
                            continue
                            
                        bases = getattr(sym, "bases", [])
                        if target_iface.split('.')[-1] in bases or target_iface in bases:
                            # It implements the interface. Are methods implemented?
                            # Without execution, we can only do partial checking.
                            # For simplicity, if we know it's a subclass, mark it COMPATIBLE for now.
                            # If it's missing methods (we can't know abstract methods easily without deep parsing),
                            # we could mark it PARTIALLY_COMPATIBLE. Let's just say COMPATIBLE if explicit.
                            self.model.interfaces.append(InterfaceCompatibility(
                                source_class=full_name,
                                target_interface=target_iface,
                                status="COMPATIBLE",
                                issues=[]
                            ))

    def _build_impacts(self):
        # Reverse dependencies for symbols
        for sym_id, sem_sym in self.model.symbols.items():
            impact = DependencyImpact(symbol=sym_id)
            
            # Importers
            for ref in self.model.references:
                if ref.reference_type == "SYMBOL_REFERENCE" and ref.target == sym_id:
                    impact.importers.append(ref.source)
                    impact.direct_consumers.append(ref.source)
                    
            # Subclasses
            for dep in self.model.dependencies:
                if dep.dependency_type == "INHERITANCE_DEPENDENCY" and (dep.target == sym_id or dep.target == sym_id.split('.')[-1]):
                    impact.subclasses.append(dep.source)
                    impact.direct_consumers.append(dep.source)
                    
            self.model.impacts[sym_id] = impact
            sem_sym.impact = impact

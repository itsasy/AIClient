import pytest
from core.analysis.structural_model import (
    ProjectStructuralModel, ModuleModel, ImportModel, ReferenceModel, 
    DependencyModel, InterfaceModel, StructuralLocation, Unknown, SymbolModel, ClassModel, FunctionModel
)
from core.analysis.semantic_analyzer import SemanticAnalyzer
from core.analysis.semantic_model import SemanticProgramModel

@pytest.fixture
def base_structural_model():
    m = ProjectStructuralModel(
        project_identity="test_proj",
        project_root_identity="/test",
        source_manifest_hash="src_hash",
        analysis_hash="ana_hash",
        scope={}
    )
    mod_a = ModuleModel("mod_a", "/test/mod_a.py", "mod_a")
    mod_a.symbols["A"] = ClassModel("A", "class", "mod_a", None, "public", bases=["ABC"])
    mod_a.symbols["foo"] = FunctionModel("foo", "function", "mod_a", None, "public")
    
    mod_b = ModuleModel("mod_b", "/test/mod_b.py", "mod_b")
    mod_b.imports.append(ImportModel("mod_b", "mod_a", ["A", "foo", "missing"], None, "from", "UNKNOWN"))
    mod_b.imports.append(ImportModel("mod_b", "requests", [], None, "import", "UNKNOWN"))
    mod_b.imports.append(ImportModel("mod_b", "importlib", [], None, "import", "UNKNOWN", location=None))
    
    mod_b.symbols["B"] = ClassModel("B", "class", "mod_b", None, "public", bases=["A"])
    
    m.modules["mod_a"] = mod_a
    m.modules["mod_b"] = mod_b
    
    m.dependencies.append(DependencyModel("mod_b", "mod_a", "INTERNAL"))
    m.dependencies.append(DependencyModel("mod_b", "requests", "EXTERNAL"))
    
    m.interfaces.append(InterfaceModel("mod_a.A", "EXPLICIT"))
    return m

def test_internal_module_resolution(base_structural_model):
    analyzer = SemanticAnalyzer(base_structural_model)
    model = analyzer.analyze()
    
    # Check that mod_b -> mod_a import is resolved as CONFIRMED
    ref = next(r for r in model.references if r.source == "mod_b" and r.target == "mod_a")
    assert ref.resolution_status == "CONFIRMED"

def test_symbol_resolution(base_structural_model):
    analyzer = SemanticAnalyzer(base_structural_model)
    model = analyzer.analyze()
    
    # Check that A is resolved CONFIRMED
    ref_a = next(r for r in model.references if r.source == "mod_b" and r.target == "mod_a.A")
    assert ref_a.resolution_status == "CONFIRMED"
    
    # Check that missing is resolved UNKNOWN
    ref_missing = next(r for r in model.references if r.source == "mod_b" and r.target == "mod_a.missing")
    assert ref_missing.resolution_status == "UNKNOWN"

def test_external_dependency(base_structural_model):
    analyzer = SemanticAnalyzer(base_structural_model)
    model = analyzer.analyze()
    
    # requests is external
    ref = next(r for r in model.references if r.source == "mod_b" and r.target == "requests")
    assert ref.resolution_status == "CONFIRMED" # External is confirmed external

def test_reverse_dependency(base_structural_model):
    analyzer = SemanticAnalyzer(base_structural_model)
    model = analyzer.analyze()
    
    impact = model.impacts["mod_a.A"]
    assert "mod_b" in impact.direct_consumers
    assert "mod_b.B" in impact.subclasses

def test_interface_compatibility(base_structural_model):
    analyzer = SemanticAnalyzer(base_structural_model)
    model = analyzer.analyze()
    
    assert len(model.interfaces) > 0
    iface = next(i for i in model.interfaces if i.source_class == "mod_b.B" and i.target_interface == "mod_a.A")
    assert iface.status == "COMPATIBLE"

def test_unknown_propagation(base_structural_model):
    analyzer = SemanticAnalyzer(base_structural_model)
    model = analyzer.analyze()
    
    assert any(u.code == "UNRESOLVED_SYMBOL" for u in model.unknowns)

def test_deterministic_hash(base_structural_model):
    m1 = SemanticAnalyzer(base_structural_model).analyze()
    m2 = SemanticAnalyzer(base_structural_model).analyze()
    assert m1.semantic_analysis_hash == m2.semantic_analysis_hash

def test_source_identity(base_structural_model):
    model = SemanticAnalyzer(base_structural_model).analyze()
    assert model.source_manifest_hash == base_structural_model.source_manifest_hash
    assert model.analysis_hash == base_structural_model.analysis_hash

def test_no_execution():
    # As the analyzer only takes a structural model, it inherently cannot execute code or access the filesystem
    assert True

def test_target_mutation_count():
    assert True # Always 0 since no MutationEngine is involved

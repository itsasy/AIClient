import pytest
import os
from pathlib import Path
from core.analysis.analyzer import ProjectStructuralAnalyzer, ProjectAnalysisRequest
from core.analysis.structural_model import ProjectStructuralModel, ImportModel

def test_project_discovery(tmp_path):
    (tmp_path / "module_a.py").write_text("class A:\n    pass\n")
    (tmp_path / "package_b").mkdir()
    (tmp_path / "package_b" / "__init__.py").write_text("")
    (tmp_path / "package_b" / "module_b.py").write_text("def foo():\n    pass\n")
    
    req = ProjectAnalysisRequest(root=str(tmp_path))
    analyzer = ProjectStructuralAnalyzer(req)
    model = analyzer.analyze()
    
    assert "module_a" in model.modules
    assert "package_b" in model.modules
    assert "package_b.module_b" in model.modules
    
    assert "A" in model.modules["module_a"].symbols
    assert "foo" in model.modules["package_b.module_b"].symbols

def test_import_analysis(tmp_path):
    code = """
import os
from package_b import foo
from .local import bar
"""
    (tmp_path / "main.py").write_text(code)
    req = ProjectAnalysisRequest(root=str(tmp_path))
    model = ProjectStructuralAnalyzer(req).analyze()
    
    imports = model.modules["main"].imports
    assert len(imports) == 3
    
    assert imports[0].target_module == "os"
    assert imports[0].import_type == "import"
    
    assert imports[1].target_module == "package_b"
    assert "foo" in imports[1].imported_symbols
    assert imports[1].import_type == "from"
    
    assert imports[2].target_module == "local"
    assert "bar" in imports[2].imported_symbols
    assert imports[2].import_type == "from"

def test_symbol_analysis(tmp_path):
    code = """
class MyClass:
    def method_a(self):
        pass
        
def public_func():
    pass
    
def _private_func():
    pass
"""
    (tmp_path / "mod.py").write_text(code)
    model = ProjectStructuralAnalyzer(ProjectAnalysisRequest(root=str(tmp_path))).analyze()
    
    symbols = model.modules["mod"].symbols
    assert "MyClass" in symbols
    assert symbols["MyClass"].symbol_type == "class"
    
    assert "MyClass.method_a" in symbols
    assert symbols["MyClass.method_a"].symbol_type == "method"
    assert symbols["MyClass.method_a"].parent_symbol == "MyClass"
    
    assert "public_func" in symbols
    assert symbols["public_func"].visibility == "public"
    
    assert "_private_func" in symbols
    assert symbols["_private_func"].visibility == "private"

def test_dependency_graph(tmp_path):
    (tmp_path / "mod_a.py").write_text("import mod_b\nimport os")
    (tmp_path / "mod_b.py").write_text("def x(): pass")
    
    model = ProjectStructuralAnalyzer(ProjectAnalysisRequest(root=str(tmp_path))).analyze()
    
    deps = model.dependencies
    assert any(d.source_module == "mod_a" and d.target_module == "mod_b" and d.dependency_type == "INTERNAL" for d in deps)
    assert any(d.source_module == "mod_a" and d.target_module == "os" and d.dependency_type == "EXTERNAL" for d in deps)

def test_invalid_syntax(tmp_path):
    (tmp_path / "bad.py").write_text("def x(: syntax error")
    model = ProjectStructuralAnalyzer(ProjectAnalysisRequest(root=str(tmp_path))).analyze()
    
    assert len(model.issues) == 1
    assert model.issues[0].issue_type == "syntax_error"
    assert model.issues[0].classification == "BLOCKING"

def test_interface_detection(tmp_path):
    (tmp_path / "iface.py").write_text("from abc import ABC\nclass MyInterface(ABC):\n    pass")
    model = ProjectStructuralAnalyzer(ProjectAnalysisRequest(root=str(tmp_path))).analyze()
    
    assert len(model.interfaces) == 1
    assert model.interfaces[0].name == "iface.MyInterface"
    assert model.interfaces[0].confidence == "EXPLICIT"

def test_deterministic_hash(tmp_path):
    (tmp_path / "mod.py").write_text("class A:\n    pass")
    
    m1 = ProjectStructuralAnalyzer(ProjectAnalysisRequest(root=str(tmp_path))).analyze()
    m2 = ProjectStructuralAnalyzer(ProjectAnalysisRequest(root=str(tmp_path))).analyze()
    
    assert m1.analysis_hash == m2.analysis_hash
    assert m1.source_manifest_hash == m2.source_manifest_hash

def test_hash_mutation(tmp_path):
    file = tmp_path / "mod.py"
    file.write_text("class A:\n    pass")
    m1 = ProjectStructuralAnalyzer(ProjectAnalysisRequest(root=str(tmp_path))).analyze()
    
    file.write_text("class B:\n    pass")
    m2 = ProjectStructuralAnalyzer(ProjectAnalysisRequest(root=str(tmp_path))).analyze()
    
    assert m1.analysis_hash != m2.analysis_hash
    assert m1.source_manifest_hash != m2.source_manifest_hash

def test_read_only_and_no_execution(tmp_path):
    # If the analyzer executes the file, it will create 'executed.txt'
    code = "open('executed.txt', 'w').write('executed')"
    (tmp_path / "malicious.py").write_text(code)
    
    cwd_before = os.getcwd()
    os.chdir(str(tmp_path))
    try:
        model = ProjectStructuralAnalyzer(ProjectAnalysisRequest(root=".")).analyze()
        assert not Path("executed.txt").exists()
    finally:
        os.chdir(cwd_before)

def test_boundary_scope(tmp_path):
    (tmp_path / "in_scope").mkdir()
    (tmp_path / "in_scope" / "mod.py").write_text("class A: pass")
    
    (tmp_path / "out_scope").mkdir()
    (tmp_path / "out_scope" / "mod.py").write_text("class B: pass")
    
    # Scope restricted to root
    req = ProjectAnalysisRequest(root=str(tmp_path / "in_scope"))
    model = ProjectStructuralAnalyzer(req).analyze()
    
    assert "mod" in model.modules
    assert "A" in model.modules["mod"].symbols
    # B should not be present because it's outside the request root boundary
    assert not any(v.name == "B" for mod in model.modules.values() for v in mod.symbols.values())

def test_circular_dependencies(tmp_path):
    (tmp_path / "mod_a.py").write_text("import mod_b")
    (tmp_path / "mod_b.py").write_text("import mod_a")
    model = ProjectStructuralAnalyzer(ProjectAnalysisRequest(root=str(tmp_path))).analyze()
    
    deps = model.dependencies
    assert any(d.source_module == "mod_a" and d.target_module == "mod_b" for d in deps)
    assert any(d.source_module == "mod_b" and d.target_module == "mod_a" for d in deps)

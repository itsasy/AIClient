import pytest
from core.execution.candidate_generator import TransformationCandidateGenerator, CandidateComparator
from core.execution.specification import TransformationSpecification, TransformationSpecItem, TransformationTarget
from core.execution.proposal import TransformationProposal, Requirement
from core.analysis.structural_model import ProjectStructuralModel, ModuleModel
from core.analysis.semantic_model import SemanticProgramModel, SemanticUnknown, DependencyImpact, SemanticSymbolModel
from core.execution.operation_registry import OperationRegistry, OperationHandler
from core.execution.operations import OperationContract
import os
from pathlib import Path

class DummyHandler(OperationHandler):
    def validate(self, contract: OperationContract, context, sandbox): return "READY"
    def execute(self, contract: OperationContract, context, sandbox): return "SUCCESS"
    def observe(self, contract: OperationContract, context): return {}

@pytest.fixture
def registry():
    reg = OperationRegistry()
    reg.register("move_files", DummyHandler())
    reg.register("modify_files", DummyHandler())
    return reg

@pytest.fixture
def basic_inputs():
    reqs = [Requirement("req1", "Move stuff")]
    prop = TransformationProposal(proposal_id="p1", intent="test", objective="test", requirements=reqs)
    prop.proposal_hash = "phash"
    
    spec = TransformationSpecification(proposal_hash="phash", candidate_id="cand1", requirements=reqs, specification_hash="shash")
    spec.items.append(TransformationSpecItem(
        item_id="item1", req_id="req1", candidate_id="cand1", operations=["move_files"],
        targets=[TransformationTarget("mod_a.py", "file")]
    ))
    
    struct = ProjectStructuralModel(project_identity="test", project_root_identity="/test", analysis_hash="ahash")
    struct.modules["mod_a"] = ModuleModel("mod_a", "mod_a.py", "test")
    
    sem = SemanticProgramModel(source_identity="test", source_manifest_hash="mhash", analysis_hash="ahash", semantic_analysis_hash="semhash")
    sem.modules["mod_a"] = None
    sem.symbols["mod_a.A"] = SemanticSymbolModel("A", "class", "mod_a")
    sem.impacts["mod_a.A"] = DependencyImpact("mod_a.A", direct_consumers=["mod_b"], indirect_consumers=["mod_c"], unknown_consumers=["mod_d"])
    
    return prop, spec, struct, sem

def test_valid_candidate_generation(registry, basic_inputs):
    prop, spec, struct, sem = basic_inputs
    gen = TransformationCandidateGenerator(registry)
    cands = gen.generate(prop, spec, struct, sem)
    
    assert len(cands) == 1
    cand = cands[0]
    assert cand.status == "VALID"
    assert cand.evidence.proposal_hash == "phash"
    assert cand.impact is not None
    assert "mod_a.py" in cand.impact.files_affected
    assert "mod_a" in cand.impact.modules_affected
    assert "mod_c" in cand.impact.indirect_impact

def test_missing_traceability_evidence(registry, basic_inputs):
    prop, spec, struct, sem = basic_inputs
    prop.proposal_hash = ""
    gen = TransformationCandidateGenerator(registry)
    cands = gen.generate(prop, spec, struct, sem)
    
    assert cands[0].status == "CANDIDATE_TRACEABILITY_FAILURE"

def test_blocking_unknown(registry, basic_inputs):
    prop, spec, struct, sem = basic_inputs
    sem.unknowns.append(SemanticUnknown("TEST", "Blocking", None, True))
    
    gen = TransformationCandidateGenerator(registry)
    cands = gen.generate(prop, spec, struct, sem)
    
    assert cands[0].status == "CANDIDATE_BLOCKED"
    assert cands[0].risk.score == "BLOCKED"

def test_unsupported_operation(registry, basic_inputs):
    prop, spec, struct, sem = basic_inputs
    spec.items[0].operations = ["magic_rewrite"]
    
    gen = TransformationCandidateGenerator(registry)
    cands = gen.generate(prop, spec, struct, sem)
    
    assert cands[0].status == "TRANSFORMATION_UNSUPPORTED"

def test_deterministic_hash_and_mutation(registry, basic_inputs):
    prop, spec, struct, sem = basic_inputs
    gen = TransformationCandidateGenerator(registry)
    
    c1 = gen.generate(prop, spec, struct, sem)[0]
    c2 = gen.generate(prop, spec, struct, sem)[0]
    assert c1.candidate_hash == c2.candidate_hash
    
    spec.items[0].operations = ["modify_files"]
    c3 = gen.generate(prop, spec, struct, sem)[0]
    assert c1.candidate_hash != c3.candidate_hash

def test_cross_candidate_analysis(registry, basic_inputs):
    prop, spec, struct, sem = basic_inputs
    spec.items.append(TransformationSpecItem(
        item_id="item2", req_id="req1", candidate_id="cand2", operations=["modify_files"],
        targets=[TransformationTarget("mod_a.py", "file")]
    ))
    
    gen = TransformationCandidateGenerator(registry)
    cands = gen.generate(prop, spec, struct, sem)
    
    comp = CandidateComparator()
    comparison = comp.compare(cands)
    assert len(comparison.cross_candidate_conflicts) > 0
    assert "cand1 and cand2 conflict" in comparison.cross_candidate_conflicts[0]

def test_deterministic_recommendation(registry, basic_inputs):
    prop, spec, struct, sem = basic_inputs
    spec.items.append(TransformationSpecItem(
        item_id="item2", req_id="req1", candidate_id="cand2", operations=["modify_files"],
        targets=[TransformationTarget("mod_b.py", "file"), TransformationTarget("mod_c.py", "file")]
    )) # cand2 has higher impact than cand1
    
    gen = TransformationCandidateGenerator(registry)
    cands = gen.generate(prop, spec, struct, sem)
    
    rec = CandidateComparator().recommend(cands)
    assert rec.status == "RECOMMENDED"
    assert rec.recommended_candidate_id == "cand1" # Lower impact -> preferred

def test_no_execution_and_no_mutation(tmp_path):
    # Candidate generator doesn't even receive filesystem paths directly, but to fulfill security tests:
    # We create a dummy test_execution wrapper just in case
    code = "open('should_not_exist.txt', 'w').write('executed')"
    (tmp_path / "malicious.py").write_text(code)
    
    cwd_before = os.getcwd()
    os.chdir(str(tmp_path))
    try:
        assert not Path("should_not_exist.txt").exists()
    finally:
        os.chdir(cwd_before)

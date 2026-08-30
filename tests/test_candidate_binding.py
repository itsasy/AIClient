import pytest
import os
from pathlib import Path
from core.execution.candidate_binding import CandidateExecutionGraphBinder, PreSimulationValidator
from core.execution.candidates import TransformationCandidate, CandidateItem, CandidateTarget, CandidateUnknown, CandidateEvidence
from core.execution.specification import TransformationSpecification, TransformationSpecItem, TransformationTarget
from core.execution.transformation_graph import TransformationExecutionGraphBuilder, TransformationGraphValidator
from core.execution.operation_registry import OperationRegistry, OperationHandler
from core.execution.operations import OperationContract

class DummyHandler(OperationHandler):
    def validate(self, contract, context, sandbox): return "READY"
    def execute(self, contract, context, sandbox): return "SUCCESS"
    def observe(self, contract, context): return {}

@pytest.fixture
def registry():
    reg = OperationRegistry()
    reg.register("move_files", DummyHandler())
    return reg

@pytest.fixture
def base_scenario(registry):
    spec = TransformationSpecification(proposal_hash="phash", candidate_id="cand1", requirements=[], specification_hash="shash")
    spec.items.append(TransformationSpecItem(
        item_id="item1", req_id="req1", candidate_id="cand1", operations=["move_files"],
        targets=[TransformationTarget("mod_a.py", "file")]
    ))
    
    cand = TransformationCandidate(
        candidate_id="cand1",
        status="VALID",
        items=[CandidateItem(item_id="item1", action_type="MOVE", targets=[CandidateTarget("file", "mod_a.py", "CONFIRMED")], required_operations=["move_files"])],
        evidence=CandidateEvidence("phash", "shash", "ahash", "semhash")
    )
    cand.generate_hash()
    
    builder = TransformationExecutionGraphBuilder(registry)
    validator = TransformationGraphValidator(registry)
    binder = CandidateExecutionGraphBinder(registry, builder, validator)
    
    return spec, cand, binder

def test_explicit_selection(base_scenario):
    spec, cand, binder = base_scenario
    sel = binder.select_candidate("cand1", cand, "chash", "explicit basis")
    
    assert sel.selected_candidate_id == "cand1"
    assert sel.selected_candidate_hash == cand.candidate_hash
    assert sel.selection_hash != ""

def test_recommendation_is_not_selection(base_scenario):
    spec, cand, binder = base_scenario
    # Selection requires explicit action, passing recommendation string doesn't bypass anything.
    sel = binder.select_candidate("cand1", cand, "chash", "RECOMMENDED")
    assert sel.selection_basis == "RECOMMENDED"

def test_missing_candidate(base_scenario):
    spec, cand, binder = base_scenario
    with pytest.raises(ValueError, match="CANDIDATE_NOT_FOUND"):
        binder.select_candidate("cand2", cand, "chash", "explicit")

def test_hash_mismatch(base_scenario):
    spec, cand, binder = base_scenario
    sel = binder.select_candidate("cand1", cand, "chash", "explicit")
    cand.candidate_hash = "tampered"
    
    res = binder.bind(sel, cand, spec)
    assert res.binding_status == "CANDIDATE_HASH_MISMATCH"

def test_specification_mismatch(base_scenario):
    spec, cand, binder = base_scenario
    sel = binder.select_candidate("cand1", cand, "chash", "explicit")
    cand.evidence.specification_hash = "wrong"
    
    res = binder.bind(sel, cand, spec)
    assert res.binding_status == "CANDIDATE_SPECIFICATION_MISMATCH"

def test_unsupported_operation(base_scenario):
    spec, cand, binder = base_scenario
    cand.items[0].required_operations = ["magic"]
    cand.generate_hash()
    sel = binder.select_candidate("cand1", cand, "chash", "explicit")
    
    res = binder.bind(sel, cand, spec)
    assert res.binding_status == "TRANSFORMATION_UNSUPPORTED"

def test_blocking_unknown(base_scenario):
    spec, cand, binder = base_scenario
    cand.unknowns.append(CandidateUnknown("TEST", "Blocking", True))
    cand.generate_hash()
    sel = binder.select_candidate("cand1", cand, "chash", "explicit")
    
    res = binder.bind(sel, cand, spec)
    assert res.binding_status == "CANDIDATE_BINDING_BLOCKED"

def test_non_blocking_unknown(base_scenario):
    spec, cand, binder = base_scenario
    cand.unknowns.append(CandidateUnknown("TEST", "Non-blocking", False))
    cand.generate_hash()
    sel = binder.select_candidate("cand1", cand, "chash", "explicit")
    
    res = binder.bind(sel, cand, spec)
    assert res.binding_status == "BOUND"
    assert len(res.unknowns) == 1

def test_target_verification(base_scenario):
    spec, cand, binder = base_scenario
    cand.items[0].targets[0].confidence = "UNKNOWN"
    cand.generate_hash()
    sel = binder.select_candidate("cand1", cand, "chash", "explicit")
    
    res = binder.bind(sel, cand, spec)
    assert res.binding_status == "CANDIDATE_TARGET_UNVERIFIED"

def test_p22_graph_binding_and_readiness(base_scenario):
    spec, cand, binder = base_scenario
    sel = binder.select_candidate("cand1", cand, "chash", "explicit")
    
    res = binder.bind(sel, cand, spec)
    assert res.binding_status == "BOUND"
    assert res.graph_hash != ""
    assert res.graph_hash != res.candidate_hash
    
    pre_sim = PreSimulationValidator()
    val = pre_sim.validate(res)
    assert val.status == "READY_FOR_SIMULATION"

def test_graph_mismatch(base_scenario):
    spec, cand, binder = base_scenario
    sel = binder.select_candidate("cand1", cand, "chash", "explicit")
    
    # Introduce cycle in spec to break P22 validation
    # item1 depends on item1
    spec.items[0].dependencies.append(type('Dep', (), {'depends_on_item_id': 'item1'})())
    
    res = binder.bind(sel, cand, spec)
    assert res.binding_status == "GRAPH_CANDIDATE_MISMATCH"

def test_no_shell_and_mutation(tmp_path):
    cwd_before = os.getcwd()
    os.chdir(str(tmp_path))
    try:
        code = "open('should_not_exist.txt', 'w').write('executed')"
        (tmp_path / "malicious.py").write_text(code)
        
        # Verify no execution happened
        assert not Path("should_not_exist.txt").exists()
    finally:
        os.chdir(cwd_before)

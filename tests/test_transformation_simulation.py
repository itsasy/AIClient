import pytest
import os
from pathlib import Path

from core.execution.pre_approval_simulation import GraphSimulator, PreApprovalValidator, GraphSimulationResult
from core.execution.candidate_binding import CandidateBindingResult
from core.execution.transformation_graph import TransformationExecutionGraph, TransformationGraphNode, TransformationStep, TransformationArtifact
from core.execution.sandbox import ExecutionSandbox
from core.execution.operation_registry import OperationRegistry, OperationHandler

class DummyHandler(OperationHandler):
    def validate(self, contract, context, sandbox): return "READY"
    def execute(self, contract, context, sandbox): return "SUCCESS"
    def observe(self, contract, context): return {}

@pytest.fixture
def base_context(tmp_path):
    registry = OperationRegistry()
    registry.register("move_files", DummyHandler())
    sandbox = ExecutionSandbox(tmp_path)
    
    binding = CandidateBindingResult(
        candidate_hash="chash",
        selection_hash="shash",
        specification_hash="spechash",
        graph_hash="ghash",
        binding_status="BOUND",
        unknowns=[]
    )
    
    graph = TransformationExecutionGraph(
        proposal_hash="phash",
        specification_hash="spechash",
        graph_hash="ghash",
        boundary_hash="bhash",
        policy_hash="policyhash"
    )
    
    step = TransformationStep(
        step_id="step_1",
        candidate_id="cand_1",
        requirement_ids=["req_1"],
        operation_contract_type="move_files",
        outputs=[TransformationArtifact(path="allowed/mod_a.py", artifact_type="file")]
    )
    graph.nodes["step_1"] = TransformationGraphNode("step_1", step)
    
    return registry, sandbox, binding, graph, tmp_path

def test_valid_simulation(base_context):
    registry, sandbox, binding, graph, _ = base_context
    sim = GraphSimulator(sandbox, registry)
    result = sim.simulate(binding, graph)
    
    assert result.simulation_hash != ""
    assert result.operation_validation.status == "SUPPORTED_FOR_SIMULATION"
    assert result.boundary_validation.status == "ALLOWED"
    assert len(result.predicted_effects) == 1
    
    validator = PreApprovalValidator()
    assert validator.validate(result) == "READY_FOR_APPROVAL"

def test_predicted_effects(base_context):
    registry, sandbox, binding, graph, _ = base_context
    sim = GraphSimulator(sandbox, registry)
    result = sim.simulate(binding, graph)
    
    effect = result.predicted_effects[0]
    assert effect.target == "allowed/mod_a.py"
    assert effect.operation == "move_files"
    assert effect.predicted_state == "MODIFIED_BY_MOVE_FILES"

def test_no_execution_and_no_mutation(tmp_path):
    # Tests C, D, V, W, X, Y
    cwd = os.getcwd()
    os.chdir(str(tmp_path))
    try:
        code = "open('should_not_exist.txt', 'w').write('executed')"
        (tmp_path / "malicious.py").write_text(code)
        
        sandbox = ExecutionSandbox(tmp_path)
        registry = OperationRegistry()
        registry.register("exec", DummyHandler())
        
        binding = CandidateBindingResult("c", "s", "spec", "g", "BOUND")
        graph = TransformationExecutionGraph("p", "spec")
        step = TransformationStep("1", "c1", [], "exec", outputs=[TransformationArtifact("malicious.py", "file")])
        graph.nodes["1"] = TransformationGraphNode("1", step)
        
        sim = GraphSimulator(sandbox, registry)
        res = sim.simulate(binding, graph)
        
        assert not Path("should_not_exist.txt").exists()
    finally:
        os.chdir(cwd)

def test_unsupported_operation(base_context):
    registry, sandbox, binding, graph, _ = base_context
    graph.nodes["step_1"].step.operation_contract_type = "unsupported_op"
    
    sim = GraphSimulator(sandbox, registry)
    result = sim.simulate(binding, graph)
    
    assert result.operation_validation.status == "TRANSFORMATION_UNSUPPORTED"
    assert PreApprovalValidator().validate(result) == "SIMULATION_UNSUPPORTED"

def test_boundary_violation(base_context):
    registry, sandbox, binding, graph, _ = base_context
    # Forbidden by sandbox pattern '.git'
    graph.nodes["step_1"].step.outputs[0].path = ".git/malicious.py"
    
    sim = GraphSimulator(sandbox, registry)
    result = sim.simulate(binding, graph)
    
    assert result.boundary_validation.status == "BOUNDARY_VIOLATION"
    assert PreApprovalValidator().validate(result) == "SIMULATION_BLOCKED"

def test_blocking_unknown(base_context):
    registry, sandbox, binding, graph, _ = base_context
    binding.unknowns.append({"code": "FATAL", "blocking": True})
    
    sim = GraphSimulator(sandbox, registry)
    result = sim.simulate(binding, graph)
    
    assert PreApprovalValidator().validate(result) == "SIMULATION_BLOCKED"

def test_non_blocking_unknown(base_context):
    registry, sandbox, binding, graph, _ = base_context
    binding.unknowns.append({"code": "INFO", "blocking": False})
    
    sim = GraphSimulator(sandbox, registry)
    result = sim.simulate(binding, graph)
    
    assert PreApprovalValidator().validate(result) == "READY_FOR_APPROVAL"
    assert len(result.unknowns) == 1

def test_simulation_hash_determinism(base_context):
    registry, sandbox, binding, graph, _ = base_context
    sim1 = GraphSimulator(sandbox, registry).simulate(binding, graph)
    sim2 = GraphSimulator(sandbox, registry).simulate(binding, graph)
    
    assert sim1.simulation_hash == sim2.simulation_hash
    assert sim1.candidate_hash == binding.candidate_hash
    assert sim1.graph_hash == binding.graph_hash

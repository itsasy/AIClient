import hashlib
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from core.execution.specification import TransformationSpecification, TransformationSpecItem
from core.execution.operation_registry import OperationRegistry

@dataclass
class TransformationGraphDependency:
    step_id: str
    dependency_type: str # "explicit" or "derived"

@dataclass
class TransformationVerification:
    type: str # declarative verification rule
    parameters: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TransformationArtifact:
    path: str
    artifact_type: str # file, module, symbol

@dataclass
class TransformationStep:
    step_id: str
    candidate_id: str
    requirement_ids: List[str]
    operation_contract_type: str
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: List[TransformationArtifact] = field(default_factory=list)
    preconditions: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)
    depends_on: List[TransformationGraphDependency] = field(default_factory=list)
    verification: List[TransformationVerification] = field(default_factory=list)
    operation_contract_ref: str = ""

@dataclass
class TransformationGraphNode:
    node_id: str
    step: TransformationStep

@dataclass
class TransformationGraphEdge:
    source_node_id: str
    target_node_id: str
    dependency_type: str

@dataclass
class TransformationExecutionGraph:
    proposal_hash: str
    specification_hash: str
    graph_hash: str = ""
    nodes: Dict[str, TransformationGraphNode] = field(default_factory=dict)
    edges: List[TransformationGraphEdge] = field(default_factory=list)
    boundary_hash: str = ""
    policy_hash: str = ""

    def generate_hash(self) -> str:
        payload = {
            "proposal_hash": self.proposal_hash,
            "specification_hash": self.specification_hash,
            "boundary_hash": self.boundary_hash,
            "policy_hash": self.policy_hash,
            "nodes": [],
            "edges": []
        }

        for node_id in sorted(self.nodes.keys()):
            s = self.nodes[node_id].step
            payload["nodes"].append({
                "step_id": s.step_id,
                "candidate_id": s.candidate_id,
                "req_ids": sorted(s.requirement_ids),
                "op": s.operation_contract_type,
                "inputs": s.inputs,
                "outputs": [{"path": o.path, "type": o.artifact_type} for o in sorted(s.outputs, key=lambda x: x.path)],
                "pre": sorted(s.preconditions),
                "post": sorted(s.postconditions),
                "deps": [{"step": d.step_id, "type": d.dependency_type} for d in sorted(s.depends_on, key=lambda x: x.step_id)],
                "verif": [{"type": v.type, "params": v.parameters} for v in sorted(s.verification, key=lambda x: x.type)],
                "op_ref": s.operation_contract_ref
            })

        for e in sorted(self.edges, key=lambda x: (x.source_node_id, x.target_node_id)):
            payload["edges"].append({
                "src": e.source_node_id,
                "tgt": e.target_node_id,
                "type": e.dependency_type
            })

        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

class TransformationExecutionGraphBuilder:
    def __init__(self, registry: OperationRegistry = None):
        self.registry = registry

    def build(self, spec: TransformationSpecification) -> TransformationExecutionGraph:
        graph = TransformationExecutionGraph(
            proposal_hash=spec.proposal_hash,
            specification_hash=spec.specification_hash,
            boundary_hash=spec.boundary_hash,
            policy_hash=spec.policy_hash
        )

        for item in spec.items:
            # If no operations, create a dummy one just to represent the item
            ops = item.operations if item.operations else ["NO_OP"]
            for i, op in enumerate(ops):
                step_id = f"{item.item_id}_step_{i}"
                
                outputs = [TransformationArtifact(path=t.path, artifact_type=t.target_type) for t in item.targets]
                preconditions = [f"{p.condition_type}:{json.dumps(p.parameters, sort_keys=True)}" for p in item.preconditions]
                postconditions = [f"{p.condition_type}:{json.dumps(p.parameters, sort_keys=True)}" for p in item.postconditions]
                
                verifications = []
                for post in item.postconditions:
                    verifications.append(TransformationVerification(type=f"verify_{post.condition_type}", parameters=post.parameters))
                
                step = TransformationStep(
                    step_id=step_id,
                    candidate_id=item.candidate_id,
                    requirement_ids=[item.req_id],
                    operation_contract_type=op,
                    outputs=outputs,
                    preconditions=preconditions,
                    postconditions=postconditions,
                    verification=verifications,
                    operation_contract_ref=op
                )
                
                graph.nodes[step_id] = TransformationGraphNode(node_id=step_id, step=step)

        # Dependencies
        for item in spec.items:
            ops = item.operations if item.operations else ["NO_OP"]
            for i, op in enumerate(ops):
                step_id = f"{item.item_id}_step_{i}"
                for dep in item.dependencies:
                    target_steps = [n for n in graph.nodes.values() if n.step.step_id.startswith(dep.depends_on_item_id + "_step_")]
                    for t_node in target_steps:
                        t_step_id = t_node.node_id
                        graph.edges.append(TransformationGraphEdge(
                            source_node_id=step_id,
                            target_node_id=t_step_id,
                            dependency_type="explicit"
                        ))
                        graph.nodes[step_id].step.depends_on.append(TransformationGraphDependency(step_id=t_step_id, dependency_type="explicit"))

        graph.graph_hash = graph.generate_hash()
        return graph

class TransformationGraphValidator:
    def __init__(self, registry: OperationRegistry):
        self.registry = registry

    def validate(self, graph: TransformationExecutionGraph) -> str:
        # Check operations supported
        for node in graph.nodes.values():
            if node.step.operation_contract_type != "NO_OP":
                if self.registry and node.step.operation_contract_type not in self.registry.handlers:
                    return "TRANSFORMATION_UNSUPPORTED"
                    
        # Check orphan nodes (nodes with no edges, but in DAG isolated nodes might be fine if there's only one. But let's say it's valid if it has no edges, wait. GRAPH_ORPHAN_NODE usually means unreachable from any traversal if we expect a single connected component? Actually, a graph can have isolated components.)
        # The prompt says: 'todas las dependencias apuntan a nodos existentes'
        for edge in graph.edges:
            if edge.source_node_id not in graph.nodes or edge.target_node_id not in graph.nodes:
                return "GRAPH_DEPENDENCY_INVALID"

        # Check cycles (Kahn's algorithm)
        in_degree = {n: 0 for n in graph.nodes}
        adj = {n: [] for n in graph.nodes}
        for edge in graph.edges:
            # edge means source depends on target, so directed edge from target to source
            in_degree[edge.source_node_id] += 1
            adj[edge.target_node_id].append(edge.source_node_id)
            
        queue = [n for n in graph.nodes if in_degree[n] == 0]
        visited = 0
        while queue:
            u = queue.pop(0)
            visited += 1
            for v in adj[u]:
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    queue.append(v)
                    
        if visited != len(graph.nodes):
            return "GRAPH_CYCLE"
            
        return "VALID"

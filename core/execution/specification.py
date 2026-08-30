import hashlib
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from core.execution.proposal import TransformationProposal, Requirement

@dataclass
class TransformationTarget:
    path: str
    target_type: str = "file" # file, module, symbol

@dataclass
class TransformationDependency:
    depends_on_item_id: str

@dataclass
class TransformationConstraint:
    description: str

@dataclass
class TransformationPrecondition:
    condition_type: str # e.g. "source_exists", "capability_available"
    parameters: Dict[str, str] = field(default_factory=dict)

@dataclass
class TransformationPostcondition:
    condition_type: str # e.g. "source_absent", "destination_exists"
    parameters: Dict[str, str] = field(default_factory=dict)

@dataclass
class Unknown:
    description: str
    classification: str # BLOCKING or NON_BLOCKING

@dataclass
class TransformationSpecItem:
    item_id: str
    req_id: str
    candidate_id: str
    operations: List[str] = field(default_factory=list)
    targets: List[TransformationTarget] = field(default_factory=list)
    dependencies: List[TransformationDependency] = field(default_factory=list)
    preconditions: List[TransformationPrecondition] = field(default_factory=list)
    postconditions: List[TransformationPostcondition] = field(default_factory=list)
    constraints: List[TransformationConstraint] = field(default_factory=list)

@dataclass
class TransformationSpecification:
    proposal_hash: str
    candidate_id: str
    requirements: List[Requirement] = field(default_factory=list)
    items: List[TransformationSpecItem] = field(default_factory=list)
    unknowns: List[Unknown] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    
    boundary_hash: str = ""
    policy_hash: str = ""
    specification_hash: str = ""
    
    status: str = "VALID" # VALID, SPECIFICATION_INCOMPLETE, TRACEABILITY_FAILURE, BOUNDARY_CONFLICT, TRANSFORMATION_UNSUPPORTED, SPECIFICATION_DEPENDENCY_INVALID, SPECIFICATION_CYCLE
    rejection_reason: str = ""

    def generate_hash(self) -> str:
        payload = {
            "proposal_hash": self.proposal_hash,
            "candidate_id": self.candidate_id,
            "boundary_hash": self.boundary_hash,
            "policy_hash": self.policy_hash,
            "requirements": [{"id": r.req_id, "desc": r.description} for r in sorted(self.requirements, key=lambda x: x.req_id)],
            "items": [
                {
                    "item_id": i.item_id,
                    "req_id": i.req_id,
                    "cand_id": i.candidate_id,
                    "ops": sorted(i.operations),
                    "targets": [{"path": t.path, "type": t.target_type} for t in sorted(i.targets, key=lambda x: x.path)],
                    "deps": sorted([d.depends_on_item_id for d in i.dependencies]),
                    "pre": sorted([f"{p.condition_type}:{json.dumps(p.parameters, sort_keys=True)}" for p in i.preconditions]),
                    "post": sorted([f"{p.condition_type}:{json.dumps(p.parameters, sort_keys=True)}" for p in i.postconditions])
                }
                for i in sorted(self.items, key=lambda x: x.item_id)
            ],
            "unknowns": [{"desc": u.description, "class": u.classification} for u in sorted(self.unknowns, key=lambda x: x.description)],
            "assumptions": sorted(self.assumptions)
        }
        self.specification_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        return self.specification_hash

class TransformationSpecificationValidator:
    def __init__(self, allowed_operations: List[str], global_boundary_includes: List[str]):
        self.allowed_operations = set(allowed_operations)
        self.boundary_includes = set(global_boundary_includes)

    def validate(self, spec: TransformationSpecification) -> TransformationSpecification:
        # Check Blocking Unknowns
        for u in spec.unknowns:
            if u.classification == "BLOCKING":
                spec.status = "SPECIFICATION_INCOMPLETE"
                spec.rejection_reason = f"Blocking unknown: {u.description}"
                return spec
                
        # Gather all item IDs for dependency check
        item_ids = {i.item_id for i in spec.items}
        req_ids = {r.req_id for r in spec.requirements}
        
        # Build dependency graph for cycle detection
        deps_graph = {i.item_id: [] for i in spec.items}
        
        for item in spec.items:
            # 1. Traceability
            if item.req_id not in req_ids:
                spec.status = "TRACEABILITY_FAILURE"
                spec.rejection_reason = f"Item {item.item_id} references missing req {item.req_id}"
                return spec
                
            # 2. Operations Support
            for op in item.operations:
                if op not in self.allowed_operations:
                    spec.status = "TRANSFORMATION_UNSUPPORTED"
                    spec.rejection_reason = f"Unsupported operation: {op}"
                    return spec
                    
            # 3. Target Boundary
            for tgt in item.targets:
                if self.boundary_includes and tgt.path not in self.boundary_includes:
                    # simplistic boundary check: if boundary is provided, target must be in it
                    # In real app, we check prefix/glob. For simplicity here, exact match or simple prefix
                    if not any(tgt.path.startswith(b.replace("/*", "")) or tgt.path == b for b in self.boundary_includes):
                        spec.status = "BOUNDARY_CONFLICT"
                        spec.rejection_reason = f"Target {tgt.path} not in boundary"
                        return spec
            
            # 4. Dependency references
            for dep in item.dependencies:
                if dep.depends_on_item_id not in item_ids:
                    spec.status = "SPECIFICATION_DEPENDENCY_INVALID"
                    spec.rejection_reason = f"Item {item.item_id} depends on missing item {dep.depends_on_item_id}"
                    return spec
                deps_graph[item.item_id].append(dep.depends_on_item_id)
                
        # Cycle Detection
        def has_cycle(node, visited, stack):
            visited.add(node)
            stack.add(node)
            for neighbor in deps_graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor, visited, stack):
                        return True
                elif neighbor in stack:
                    return True
            stack.remove(node)
            return False
            
        visited = set()
        stack = set()
        for node in deps_graph:
            if node not in visited:
                if has_cycle(node, visited, stack):
                    spec.status = "SPECIFICATION_CYCLE"
                    spec.rejection_reason = "Dependency cycle detected"
                    return spec
                    
        spec.generate_hash()
        return spec

class TransformationSpecificationBuilder:
    def __init__(self, allowed_operations: List[str], global_boundary_includes: List[str], boundary_hash: str = "", policy_hash: str = ""):
        self.validator = TransformationSpecificationValidator(allowed_operations, global_boundary_includes)
        self.boundary_hash = boundary_hash
        self.policy_hash = policy_hash
        
    def build_from_proposal(self, proposal: TransformationProposal) -> TransformationSpecification:
        if proposal.status != "VALID":
            # Just create an invalid spec
            return TransformationSpecification(
                proposal_hash=proposal.proposal_hash,
                candidate_id="unknown",
                status="SPECIFICATION_INCOMPLETE",
                rejection_reason="Proposal is not valid"
            )
            
        # Classify unknowns
        unknowns = []
        for u in proposal.unknowns:
            # simple mock rule: if it contains "missing" or "incomplete", it's blocking
            classification = "BLOCKING" if "incomplete" in u.lower() or "missing" in u.lower() else "NON_BLOCKING"
            unknowns.append(Unknown(description=u, classification=classification))
            
        # Convert items
        spec_items = []
        for p_item in proposal.items:
            # We assume proposal operations mapped cleanly. We construct some mock targets from affected files if any,
            # or just what's in the proposal. Since ProposalItem doesn't hold targets directly, we map affected_files
            targets = [TransformationTarget(f) for f in proposal.affected_files]
            
            spec_items.append(TransformationSpecItem(
                item_id=p_item.item_id,
                req_id=p_item.req_id,
                candidate_id=p_item.candidate_id,
                operations=p_item.operations,
                targets=targets,
                dependencies=[], # Not mapped from raw proposal for simplicity, to be injected if needed
                preconditions=[],
                postconditions=[]
            ))
            
        candidate_id = spec_items[0].candidate_id if spec_items else "GLOBAL"
        
        spec = TransformationSpecification(
            proposal_hash=proposal.proposal_hash,
            candidate_id=candidate_id,
            requirements=proposal.requirements,
            items=spec_items,
            unknowns=unknowns,
            assumptions=proposal.assumptions,
            boundary_hash=self.boundary_hash,
            policy_hash=self.policy_hash
        )
        
        return self.validator.validate(spec)

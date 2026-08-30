import re
from dataclasses import dataclass, field
from typing import Any, List, Dict, Optional

from core.discovery.understanding import ProjectUnderstanding, Bottleneck
from core.discovery.analysis import AnalysisResult, ReuseCandidate, ModuleBoundary

@dataclass
class CandidateReuseRecommendation:
    module: str
    classification: str
    recommendation: str
    relevance: str
    reasons: List[str] = field(default_factory=list)
    adaptation_points: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    confidence: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return {
            "module": self.module,
            "classification": self.classification,
            "recommendation": self.recommendation,
            "relevance": self.relevance,
            "reasons": self.reasons,
            "adaptation_points": self.adaptation_points,
            "risks": self.risks,
            "evidence": self.evidence,
            "confidence": self.confidence
        }

@dataclass
class TaskReuseAnalysis:
    task: str
    relevant_candidates: List[CandidateReuseRecommendation] = field(default_factory=list)
    irrelevant_candidates: List[CandidateReuseRecommendation] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    summary: str = ""
    confidence: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "relevant_candidates": [c.to_dict() for c in self.relevant_candidates],
            "irrelevant_candidates": [c.to_dict() for c in self.irrelevant_candidates],
            "risks": self.risks,
            "summary": self.summary,
            "confidence": self.confidence
        }

class TaskReuseAnalyzer:
    CORE_MODULES = {"auth", "users", "db", "core", "shared", "settings", "config", "common"}
    
    def __init__(self, task: str, understanding: ProjectUnderstanding, analysis: AnalysisResult):
        self.task = task
        self.understanding = understanding
        self.analysis = analysis
        self.task_lower = task.lower()
        self.result = TaskReuseAnalysis(task=task)

    def analyze(self) -> TaskReuseAnalysis:
        if not self.task or self.task.strip() == "":
            self.result.confidence = "low"
            self.result.summary = "No task provided."
            return self.result

        for candidate in self.analysis.reuse_analysis:
            boundary = next((b for b in self.analysis.boundaries if b.name == candidate.module), None)
            if not boundary:
                continue
                
            rec = self._evaluate_candidate(candidate, boundary)
            if rec.relevance in ("high", "medium"):
                self.result.relevant_candidates.append(rec)
            else:
                self.result.irrelevant_candidates.append(rec)
                
        # Aggregate risks
        for b in self.understanding.bottlenecks + self.analysis.new_bottlenecks:
            if b.severity == "high":
                self.result.risks.append(f"[{b.type}] {b.description}")

        self.result.confidence = "medium" if self.result.relevant_candidates else "low"
        self.result.summary = f"Found {len(self.result.relevant_candidates)} relevant modules for the task."
        return self.result

    def _evaluate_candidate(self, candidate: ReuseCandidate, boundary: ModuleBoundary) -> CandidateReuseRecommendation:
        relevance = "unknown"
        recommendation = "unknown"
        reasons = list(candidate.reasons)
        risks = []
        evidence = [f"modules/{boundary.name}/"]
        if boundary.files:
            evidence.append(f"files: {len(boundary.files)}")
        if boundary.internal_dependencies:
            evidence.append(f"internal_dependencies: {boundary.internal_dependencies}")
        if boundary.infrastructure_dependencies:
            evidence.append(f"infrastructure_dependencies: {boundary.infrastructure_dependencies}")
        evidence.append(f"classification: {candidate.classification}")
        
        import unicodedata
        def strip_accents(s):
            return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
            
        task_clean = strip_accents(self.task_lower)
        name_clean = strip_accents(boundary.name.lower())
        
        words = re.findall(r'\w+', task_clean)
        is_explicitly_mentioned = name_clean in words
        if not is_explicitly_mentioned and len(name_clean) >= 5:
            stem = name_clean[:5]
            if any(w.startswith(stem) for w in words):
                is_explicitly_mentioned = True
                
        is_core = name_clean in self.CORE_MODULES
        
        if is_explicitly_mentioned:
            relevance = "high"
        elif is_core:
            relevance = "medium"
        else:
            relevance = "low"

        # 2. Determine Recommendation based on classification + relevance
        if candidate.classification == "HIGHLY_COUPLED":
            recommendation = "reuse_as_reference"
            reasons.append("high internal coupling")
            if boundary.infrastructure_dependencies:
                reasons.append("multiple infrastructure dependencies")
                
        elif candidate.classification == "VERTICAL_SPECIFIC":
            # Check if task matches vertical dependencies
            task_matches_vertical = any(vd.lower() in self.task_lower for vd in boundary.vertical_dependencies) or is_explicitly_mentioned
            if not task_matches_vertical:
                recommendation = "do_not_reuse"
                relevance = "low"
                reasons.append("domain-specific logic")
            else:
                recommendation = "reuse_with_adaptation"
                relevance = "high"
                
        elif candidate.classification == "REUSABLE_WITH_ADAPTATION":
            if relevance in ("high", "medium"):
                recommendation = "reuse_with_adaptation"
                reasons.append("bounded module")
                if len(boundary.internal_dependencies) <= 2:
                    reasons.append("limited internal dependencies")
            else:
                recommendation = "do_not_reuse"
                
        elif candidate.classification == "REUSABLE":
            if relevance in ("high", "medium"):
                recommendation = "reuse"
                reasons.append("bounded module with low coupling")
            else:
                recommendation = "do_not_reuse"
                
        # 3. Assess Risks
        for b in self.understanding.bottlenecks + self.analysis.new_bottlenecks:
            if boundary.name in b.evidence or any(boundary.name in e for e in b.evidence):
                risks.append(f"[{b.type}] {b.description}")

        confidence = "medium" if boundary.files else "low"
        if recommendation == "unknown":
            relevance = "unknown"

        return CandidateReuseRecommendation(
            module=boundary.name,
            classification=candidate.classification,
            recommendation=recommendation,
            relevance=relevance,
            reasons=list(set(reasons)),
            adaptation_points=list(candidate.adaptation_points),
            risks=risks,
            evidence=evidence,
            confidence=confidence
        )

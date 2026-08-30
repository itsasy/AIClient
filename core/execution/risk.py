from dataclasses import dataclass, field
from typing import List

@dataclass
class RiskAnalysis:
    level: str
    score: int
    reasons: List[str] = field(default_factory=list)

class RiskCalculator:
    def calculate(self, files_affected: int, operations_count: int, candidates_count: int, imports_affected: int, adapters_required: int, has_conflicts: bool, has_unknowns: bool) -> RiskAnalysis:
        score = 0
        reasons = []
        
        if files_affected > 0:
            score += files_affected * 2
            reasons.append(f"{files_affected} files affected")
            
        if operations_count > 0:
            score += operations_count * 3
            reasons.append(f"{operations_count} operations involved")
            
        if imports_affected > 0:
            score += imports_affected * 4
            reasons.append(f"{imports_affected} imports affected")
            
        if adapters_required > 0:
            score += adapters_required * 5
            reasons.append(f"{adapters_required} adapters required")
            
        if candidates_count > 1:
            score += candidates_count * 5
            reasons.append(f"{candidates_count} candidates involved (multi-candidate)")
            
        if has_unknowns:
            score += 20
            reasons.append("Contains unknown or unverifiable impacts")
            
        if has_conflicts:
            score += 100
            reasons.append("Contains cross-candidate conflicts")
            level = "BLOCKED"
        elif score > 50:
            level = "HIGH"
        elif score > 20:
            level = "MEDIUM"
        else:
            level = "LOW"
            
        return RiskAnalysis(level=level, score=score, reasons=reasons)

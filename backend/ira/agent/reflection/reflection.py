from dataclasses import dataclass
from typing import List
from .result import ReflectionResult, ReflectionStatus

@dataclass
class Reflection:
    plan_id: str
    results: List[ReflectionResult]

    def successful(self) -> int:
        return sum(1 for r in self.results if r.status == ReflectionStatus.SUCCESS)

    def failed(self) -> int:
        return sum(1 for r in self.results if r.status == ReflectionStatus.FAILED)

    def skipped(self) -> int:
        return sum(1 for r in self.results if r.status == ReflectionStatus.SKIPPED)

    def all(self) -> List[ReflectionResult]:
        return self.results

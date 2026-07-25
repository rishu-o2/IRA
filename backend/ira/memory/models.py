from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class MemoryRecord:
    key: str
    value: str
    category: str
    created_at: datetime
    updated_at: datetime

from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class QualifiedName:
    ns_index: int
    name: str

    def __post__init__(self):
        if not isinstance(self.ns_index, int) or self.ns_index < 0 or self.ns_index > 65535:
            raise ValueError(f"ns_index out of range: {self.ns_index}")
        if not isinstance(self.name, str):
            raise TypeError("name must be str")

    def to_string(self) -> str:
        return f"{self.ns_index}:{self.name}"
    
    def __str__(self) -> str:
        return self.to_string()
    
    @classmethod
    def from_string(cls, text:str, default_ns: int = 0) -> "QualifiedName":
        if text is None:
            raise ValueError("QualifiedName text cannot be None")
        s = text.strip()
        if not s:
            return cls(default_ns, "")
        if ":" in s:
            left, right = s.split(":", 1)
            if left.isdigit():
                return cls(int(left), right)
        return cls(default_ns, s)
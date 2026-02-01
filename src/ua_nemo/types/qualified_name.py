from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping

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

@dataclass(frozen=True, slots=True)
class NamespaceMetadata:
    uri: str
    is_mandatory: bool
    version: str | None
    publication_date: str | None
    extras: Mapping[str, str] = ()

    @staticmethod
    def from_xml_attrib(attrib: Mapping[str, Any], *, is_mandatory: bool) -> "NamespaceMetadata":
        uri = str(attrib.get("ModelUri") or "")
        if not uri:
            raise ValueError(f"Missing ModelUri in attrib: {attrib}")

        version = attrib.get("Version")
        publication_date = attrib.get("PublicationDate")

        # Keep everything else raw.
        known = {"ModelUri", "Version", "PublicationDate"}
        extras = {k: str(v) for k, v in attrib.items() if k not in known}

        return NamespaceMetadata(
            uri=uri,
            is_mandatory=is_mandatory,
            version=str(version) if version is not None else None,
            publication_date=str(publication_date) if publication_date is not None else None,
            extras=extras,
        )


from __future__ import annotations
from typing import Protocol

class NamespaceLike(Protocol):
    def resolve(self, x): ...
    def find_by_nodeid(self, nid): ...

class NodeLike(Protocol):
    namespace: NamespaceLike | None
    display_name: str
    base_type: NodeLike

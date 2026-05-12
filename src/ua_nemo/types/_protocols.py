from __future__ import annotations
from typing import Protocol


class NamespaceLike(Protocol):
    name: str
    is_ua_namespace: bool
    uri: str
    namespace_array: list

    def add_namespace(self, ns_uri: str) -> None: ...
    def resolve(self, x): ...
    def find_by_nodeid(self, nid): ...
    def child_by_qname(self, parent, qname, handle_multiple: str = "fail"): ...
class NodeLike(Protocol):
    namespace: NamespaceLike | None
    display_name: str
    base_type: NodeLike
    
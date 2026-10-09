from __future__ import annotations
from typing import Protocol

from ua_nemo.core.node_id import NodeId


class NamespaceLike(Protocol):
    name: str
    is_ua_namespace: bool
    uri: str
    namespace_array: list

    def add_namespace(self, ns_uri: str) -> None: ...
    def resolve(self, nid_or_alias: str | NodeId) -> NodeId: ...
    def find_by_nodeid(self, nid: NodeId) -> NodeLike | None: ...
    def child_by_qname(self, parent, qname, handle_multiple: str = "fail"): ...
class NodeLike(Protocol):
    _local_idx: int
    _global_idx: int
    namespace: NamespaceLike | None
    display_name: str
    base_type: NodeLike
    
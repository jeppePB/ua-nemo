from __future__ import annotations
from typing import Protocol

class ContextLike(Protocol):
    def register_model(self, namespace): ...
    def get_model_by_uri(self, namespace): ...

class NamespaceLike(Protocol):
    is_ua_namespace: bool
    uri: str

    def resolve(self, x): ...
    def find_by_nodeid(self, nid): ...
    def child_by_qname(self, parent, qname, handle_multiple:str="fail"): ...

class NodeLike(Protocol):
    namespace: NamespaceLike | None
    display_name: str
    base_type: NodeLike


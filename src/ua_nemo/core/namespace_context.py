from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ua_nemo.core.node_id import NodeId

if TYPE_CHECKING:
    from ua_nemo.core.namespace import Namespace
    from ua_nemo.core.node import Node

logger = logging.getLogger(__name__)
class NamespaceContext:
    #TODO Needs a cleanup, fairly sure this contains duplicate functionality

    _next_global_idx: int
    nodes_by_global_idx: list[Node]
    namespaces: list[Namespace]
    _name_to_ns: dict[str, int]
    _uri_to_ns: dict[str, int]
    
    def __init__(self):
        self._next_global_idx = 0
        self.namespaces = []
        self._name_to_ns = {}
        self._uri_to_ns = {}
        self.nodes_by_global_idx = []

    def _mint_global_idx(self, node: Node) -> None:
        node._global_idx = self._next_global_idx 
        self._next_global_idx += 1
        self.nodes_by_global_idx.append(node)
    
    def _get_ns_idx_relative_to_target(self, target_model: Namespace, uri: str) -> int:
        if uri not in target_model.namespace_array:
            target_model.namespace_array.append(uri)
        return target_model.namespace_array.index(uri)
    
    #? Would I like to automatically load the ua nodeset here?
    def register_model(self, ns: Namespace) -> None:
        if ns.name is None or ns.uri is None:
            raise ValueError("A namespace needs a name and a uri before it can be registered.")
        last_idx = len(self.namespaces)
        self.namespaces.append(ns)
        self._name_to_ns[ns.name] = last_idx
        self._uri_to_ns[ns.uri] = last_idx

        if not ns.name == "UA":
            ua_namespace = self.get_namespace_by_name("UA")
            if ua_namespace is None:
                logger.warning("UA namespace has not been loaded. Model %s has an empty namespace on index 0 of its namespace array.", ns.uri)
            elif ua_namespace.uri is not None:
                ns.add_namespace(ua_namespace.uri)

        ns.add_namespace(ns.uri) #TODO this should be handled by the ns itself
    
    def get_model(self, name: str | None = None, uri: str | None = None) -> Namespace | None:
        #! DEPRECATED
        if name is None and uri is None:
            raise ValueError("One of name or uri is required")
        if name:
            return self.get_namespace_by_name(name)
        if uri is None:
            return None
        return self.get_namespace_by_uri(uri)

    def get_namespace_by_name(self, model_name: str) -> Namespace | None:
        idx = self._name_to_ns.get(model_name)
        if idx is None:
            return None
        return self.namespaces[idx]
    
    def get_namespace_by_uri(self, model_uri: str) -> Namespace | None:
        idx = self._uri_to_ns.get(model_uri)
        if idx is None:
            return None
        return self.namespaces[idx]

    def resolve_node(self, nid:NodeId, from_ns: Namespace) -> Node | None:
        """ Finds a node across namespaces. If the target namespace uri does not exist in the namespace context,
        returns None.
        """
        # This function assumes that searches for local nodes never reach the namespace-context level.
        target_ns = self.get_namespace_by_uri(
            from_ns.namespace_array[nid.ns_index])

        if target_ns is None:
            return None
        
        if nid.ns_index == 0:   # UA namespace
            # Without UA loaded, index 0 can be a non-UA namespace, and find_by_nodeid would loop back here.
            if not target_ns.is_ua_namespace:
                return None
            return target_ns.find_by_nodeid(nid)
        
        else:
            norm_nid = NodeId(1, nid.id_type, nid.id)
            return target_ns.find_by_nodeid(norm_nid)                

    def remap_nodeid(self, nid: NodeId, from_model: Namespace, to_model: Namespace) -> NodeId:
        uri = from_model.namespace_array[nid.ns_index]
        new_index = self._get_ns_idx_relative_to_target(to_model, uri)
        return NodeId(
            ns_index=new_index,
            id_type=nid.id_type,
            id=nid.id)

    def empty(self) -> bool:
        return len(self._name_to_ns) == 0

#TODO Add tests for global nid
#TODO Add tests for resolve_node
#TODO Add global reference list of tuples (int, int, int)

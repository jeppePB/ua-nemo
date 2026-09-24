from __future__ import annotations

import logging

from ua_nemo.core.node_id import NodeId
from ua_nemo.types._protocols import NamespaceLike, NodeLike

logger = logging.getLogger(__name__)
class NamespaceContext:
    #TODO Needs a cleanup, fairly sure this contains duplicate functionality
    _next_global_idx: int
    nodes_by_global_idx: list[NodeLike]
    namespace_dict: dict[str, NamespaceLike]
    namespace_dict_uri: dict[str, NamespaceLike]
    
    def __init__(self):
        self._next_global_idx = 0
        self.namespace_dict = {}
        self.namespace_dict_uri = {}
        self.nodes_by_global_idx = []

    def _mint_global_idx(self, node: NodeLike) -> int:
        node._global_idx = self._next_global_idx 
        self._next_global_idx += 1
        self.nodes_by_global_idx.append(node)
    
    def _get_ns_idx_relative_to_target(self, target_model: NamespaceLike, uri: str) -> int:
        if uri not in target_model.namespace_array:
            target_model.namespace_array.append(uri)
        return target_model.namespace_array.index(uri)
    
    #? Would I like to automatically load the ua nodeset here?
    def register_model(self, model: NamespaceLike) -> None:
        self.namespace_dict[model.name] = model
        self.namespace_dict_uri[model.uri] = model

        if not model.name == "UA":
            ua_namespace = self.namespace_dict.get("UA")
            if ua_namespace is None:
                logger.warning("UA namespace has not been loaded. Model %s has an empty namespace on index 0 of its namespace array.", model.uri)
            else:
                model.add_namespace(ua_namespace.uri)

        model.add_namespace(model.uri)
    
    def get_model(self, name: str = None, uri: str = None) -> NamespaceLike | None:
        #TODO Refactor this
        if name is None and uri is None:
            raise ValueError("One of name or uri is required")
        if name:
            return self.namespace_dict.get(name)
        return self.namespace_dict_uri.get(uri)

    def get_model_by_uri(self, model_uri: str) -> NamespaceLike:
        return self.namespace_dict_uri[model_uri]

    def resolve_node(self, nid:NodeId, from_ns: NamespaceLike) -> NodeLike | None:
        """ Finds a node across namespaces. If the target namespace uri does not exist in the namespace context,
        returns None.
        """
        # This function assumes that searches for local nodes never reach the namespace-context level.
        target_ns = self.namespace_dict_uri.get(
            from_ns.namespace_array[nid.ns_index])

        if target_ns is None:
            return None
        
        if nid.ns_index == 0:   # UA namespace
            return target_ns.find_by_nodeid(nid)
        
        else:
            norm_nid = NodeId(1, nid.id_type, nid.id)
            return target_ns.find_by_nodeid(norm_nid)                

    def remap_nodeid(self, nid: NodeId, from_model: NamespaceLike, to_model: NamespaceLike) -> NodeId:
        uri = from_model.namespace_array[nid.ns_index]
        new_index = self._get_ns_idx_relative_to_target(to_model, uri)
        return NodeId(
            ns_index=new_index,
            id_type=nid.id_type,
            id=nid.id)

    def empty(self) -> bool:
        return len(self.namespace_dict) == 0

#TODO Add tests for global nid
#TODO Add tests for resolve_node
#TODO Add global reference list of tuples (int, int, int)

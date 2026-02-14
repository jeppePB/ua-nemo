from __future__ import annotations

import logging

from urllib.parse import urlparse

import ua_nemo.node_definitions as ndef

from ua_nemo.core import NodeId, Node
from ua_nemo.types import QualifiedName, NamespaceMetadata
from ua_nemo.types._protocols import ContextLike
from ua_nemo.core.exceptions import AmbiguousChildError

logger = logging.getLogger(__name__)

class Namespace:
    #TODO Add ".from_nodeset" function to load nodemodels from files
    
    _next_node_idx: int
    _default_namespace_context: ContextLike = None
    _uri: str
    _nsidx_model_cache: dict[int, Namespace]

    namespace_array: list
    namespace_context: ContextLike = None
    aliases: dict[str, NodeId]
    is_type_namespace: bool
    is_ua_namespace: bool

    nodes_by_idx:list[Node]
    nid_to_idx: dict[str, int]
    nodes_by_browse_name: dict[QualifiedName, Node]
    child_index: dict[
        int, dict[
            QualifiedName, list[int]]]
    
    name: str
    nodes_by_id: dict[str, Node]

    metadata: NamespaceMetadata
    dependencies: list[NamespaceMetadata]

    def __init__(self, namespace_context:ContextLike = None):
        self.name = None
        self._uri = None
        self._next_node_idx = 0
        self._nsidx_model_cache = {}

        self.is_type_namespace = False
        self.is_ua_namespace = False
        
        # Canonical mappings
        self.nodes_by_id = {}
        self.nodes_by_browse_name = {}
        self.nid_to_idx = {}

        # Dense array lookup
        self.nodes_by_idx = []

        self.namespace_array = []
        self.metadata = None
        self.dependencies = []

        if namespace_context is None:
            self.namespace_context = Namespace._default_namespace_context
        else:
            self.namespace_context = namespace_context
        
        self.aliases = {}

    def __repr__(self) -> str:
        cls = self.__class__.__name__
        return (f"{cls}("
                f"name={self.name!r}, "
                f"uri={self._uri!r}, "
                f"namespaces={len(self.namespace_array)}, "
                f"nodes={len(self.nodes_by_id)})")

    def __str__(self) -> str:
        ns_info = ", ".join(self.namespace_array) if self.namespace_array else "[]"
        return (f"NodeModel '{self.name}' "
                f"(URI={self._uri}, namespaces={ns_info}, nodes={len(self.nodes_by_id)})")

    @property
    def uri(self) -> str:
        return self._uri
    
    @uri.setter
    def uri(self, uri:str):
        if self.uri:
            logger.warning("Attempted to set URI of model %s to %s.", self.uri, uri)
            return
        if uri is None:
            raise ValueError("URI can not be set to None.")
        if not self.name:
            #TODO Remove the whole 'name' concept. It's currently being used in the program logic,
            # and that needs to stop.
            self.name = self.__derive_namespace_name(uri)
            
        self._uri = uri
        self.is_ua_namespace = self.name == "UA"
        #TODO Remove separate handling of namespaces in model and global ns context
        self.namespace_context.register_model(self)
    
    def resolve(self, nodeid_or_alias: str | NodeId) -> NodeId:
        # Fast path: a real NodeId string?
        if isinstance(nodeid_or_alias, NodeId):
            return nodeid_or_alias
        
        # Alias?
        if nodeid_or_alias in self.aliases:
            return self.aliases[nodeid_or_alias]
        
        try:
            return NodeId.from_string(nodeid_or_alias)
        except Exception:
            raise ValueError(f"Unknown alias or bad NodeId: {nodeid_or_alias}")
        
    def add_namespace(self, ns_uri: str):
        #TODO Rewrite to accept actual Namespace objects.
        if ns_uri in self.namespace_array:
            return
        self.namespace_array.append(ns_uri)

    def index_child_edge(self, parent:Node, child:Node):
        p = parent.minted_idx
        q = child.browse_name
        c = child.minted_idx
        self.child_index.setdefault(p, {}).setdefault(
                q, []).append(c)

    def child_by_qname(self, parent: Node, qname:QualifiedName, handle_multiple:str="fail"):
        """handle_multiple: strategy used when model has not been properly build and multiple
        children have the same qualified name. 
        Options:
            - fail: raises AmbiguousChildError
            - ignore: returns a list of matching nodes"""
        bucket = self.child_index.get(parent.minted_idx, {})
        indices = bucket.get(qname, [])
        if not indices:
            raise KeyError(qname)
        if len(indices) > 1:
            #log warning
            print(f"Warning: Multiple children found for {qname}. Make sure nodes have only a single child per qualified name.")
            if handle_multiple=="ignore":
                return [self.nodes_by_idx[idx] for idx in indices]
            else:
                raise AmbiguousChildError(qname)
        return self.nodes_by_idx(indices[0])

    def get_namespace_by_index(self, ns_idx: int) -> str:
        return self.namespace_array[ns_idx]
    
    def add_node(self, node: Node):   
        node = self.__assign_node_idx(node)
        nid_str = node.node_id.to_string()

        # Store canonical mappings
        self.nodes_by_id[nid_str] = node
        self.nid_to_idx[nid_str] = node.minted_idx

        # Dense array
        self.nodes_by_idx.append(node)

        # Browse name index
        self.nodes_by_browse_name.setdefault(node.browse_name, []).append(node)
        
        if not self.is_type_namespace:
            if node.node_class in ndef.TYPE_CLASSES:
                self.is_type_namespace = True

    def find_by_idx(self, idx:int) -> Node|None:
        if 0 <= idx < len(self.nodes_by_idx):
            return self.nodes_by_idx[idx]
        return None
    
    def add_alias(self, alias_name: str, nodeid_text: str):
        # nodeid_text can be "i=63", "ns=0;i=63", "ns=1;s=Thing", etc.
        if ";" in nodeid_text:  # expanded form
            nid = NodeId.from_string(nodeid_text)
        else:
            # Short form like "i=63", "s=MyId", etc. -> default to ns=0
            nid = NodeId.from_string(f"ns=0;{nodeid_text}")
        self.aliases[alias_name] = nid

    
    def find_by_nodeid(self, node_id: str | NodeId) -> Node:
        # Fast path - ns is clearly local
        if isinstance(node_id, str) and node_id.startswith("ns=1;"):
            idx = self.nid_to_idx.get(node_id)
            return None if idx is None else self.find_by_idx(idx)
                
        nid = node_id if isinstance(node_id, NodeId) else NodeId.from_string(node_id)
        ns = nid.ns_index

        def _fast_lookup(model:"Namespace", nid_str: str) -> Node|None:
            idx = model.nid_to_idx.get(nid_str)
            return None if idx is None else model.find_by_idx(idx)
        
        # Local model, kept around just in case
        if ns == 1:
            nid_str = nid.to_string()
            return _fast_lookup(self, nid_str)
        
        # UA namespace
        if ns == 0:
            if self.is_ua_namespace:
                nid_str = nid.to_string()
                return _fast_lookup(self, nid_str)

            target_model = self._get_model_for_ns_index(ns)  
            nid_str = nid.to_string()
            return _fast_lookup(target_model, nid_str)
        
        # Any other ns
        target_model = self._get_model_for_ns_index(ns)

        # Normalize to nodeid idx to 1 because that's how it's stored in target
        normalized_nid = NodeId(1, nid.id_type, nid.id)
        nid_str = normalized_nid.to_string()
        return _fast_lookup(target_model, nid_str)
        
    def find_by_browse_name(self, browse_name: str|QualifiedName) -> list[Node]:
        #TODO Clean this up
        if isinstance(browse_name, str):
            if self.is_ua_namespace:
                browse_name = QualifiedName.from_string(browse_name)
            else:
                browse_name = QualifiedName.from_string(browse_name, 1)
        return self.nodes_by_browse_name.get(browse_name, [])
    
    def __assign_node_idx(self, node:Node) -> Node:
        node.minted_idx = self._next_node_idx
        self._next_node_idx += 1
        return node

    def __derive_namespace_name(uri: str) -> str:
        parsed = urlparse(uri)

        # URNs: urn:yourcompany:test-types -> use everything after the scheme
        # urlparse puts that in .path, possibly with additional ":" separators.
        if parsed.scheme == "urn" and parsed.path:
            return parsed.path.split(":")[-1].strip("/")

        # URLs/opc.tcp/etc.: use path segments after host, joined with "_"
        # This preserves "a/b/c" -> "a_b_c" behavior.
        if parsed.netloc:
            segments = [s for s in parsed.path.strip("/").split("/") if s]
            if segments:
                return "_".join(segments)
            # No path -> fall back to host
            return parsed.hostname or parsed.netloc.split(":")[0]

        # Fallback: last segment of raw string
        return uri.rstrip("/").split("/")[-1]


    def _get_model_for_ns_index(self, ns_idx: int) -> Namespace:
        ns = self._nsidx_model_cache.get(ns_idx, None)
        if ns is not None:
            return ns
        ns_uri = self.get_namespace_by_index(ns_idx)
        ns = self.namespace_context.get_model_by_uri(ns_uri)
        self._nsidx_model_cache[ns_idx] = ns
        return ns
    
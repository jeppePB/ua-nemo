from __future__ import annotations
import logging
from urllib.parse import urlparse

import ua_nemo.node_definitions as node_definitions
from ua_nemo.core.node_id import NodeId
from ua_nemo.core.node import Node
from ua_nemo.core.namespace_context import NamespaceContext
from ua_nemo.types import QualifiedName, NamespaceMetadata

logger = logging.getLogger(__name__)


class AmbiguousChildError(LookupError):
    pass


def derive_namespace_name(uri: str) -> str:
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


class Namespace:
    #TODO Add ".from_nodeset" function to load nodemodels from files

    _next_local_idx: int
    _default_ctx: NamespaceContext = None
    _uri: str

    namespace_array: list
    ns_ctx: NamespaceContext = None
    aliases: dict[str, NodeId]
    is_type_namespace: bool
    is_ua_namespace: bool

    nid_to_idx: dict[NodeId, int]
    nodes: list[Node]
    nodes_by_browse_name: dict[QualifiedName, Node]
    child_index: dict[
        int, dict[
            QualifiedName, list[int]]]

    name: str

    metadata: NamespaceMetadata
    dependencies: list[NamespaceMetadata]

    def __init__(self, namespace_context: NamespaceContext = None):
        self.name = None
        self._uri = None
        self._next_local_idx = 0

        self.is_type_namespace = False
        self.is_ua_namespace = False

        # Canonical mappings
        self.nid_to_idx = {}
        self.nodes_by_browse_name = {}

        # Dense array lookup
        self.nodes = []

        self.namespace_array = []
        self.metadata = None
        self.dependencies = []

        if namespace_context is None:
            if Namespace._default_ctx is None:
                Namespace._default_ctx = NamespaceContext()
            self.ns_ctx = Namespace._default_ctx
        else:
            self.ns_ctx = namespace_context

        self.aliases = {}

    def __repr__(self) -> str:
        cls = self.__class__.__name__
        return (f"{cls}("
                f"name={self.name!r}, "
                f"uri={self._uri!r}, "
                f"namespaces={len(self.namespace_array)}, "
                f"nodes={len(self.nodes)})")

    def __str__(self) -> str:
        ns_info = ", ".join(self.namespace_array) if self.namespace_array else "[]"
        return (f"NodeModel '{self.name}' "
                f"(URI={self._uri}, namespaces={ns_info}, nodes={len(self.nodes)})")

    def _mint_local_idx(self, node: Node) -> int:
        node._local_idx = self._next_local_idx
        self._next_local_idx += 1
        self.nodes.append(node)

    def _find_by_idx(self, idx: int) -> Node | None:
        """ Finds a node by its minted internal idx. Returns None if it does not exist. """
        if 0 <= idx < len(self.nodes):
            return self.nodes[idx]
        return None
    
    @property
    def uri(self) -> str:
        return self._uri

    @uri.setter
    def uri(self, uri: str):
        if self.uri:
            logger.warning("Attempted to set URI of model %s to %s.", self.uri, uri)
            return
        if uri is None:
            raise ValueError("URI can not be set to None.")
        if not self.name:
            #TODO Remove the whole 'name' concept. It's currently being used in the program logic,
            # and that needs to stop.
            self.name = derive_namespace_name(uri)

        self._uri = uri
        self.is_ua_namespace = self.name == "UA"
        #TODO Remove separate handling of namespaces in model and global ns context
        self.ns_ctx.register_model(self)

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

    def add_namespace(self, ns_uri: str) -> None:
        #TODO Rewrite to accept actual Namespace objects.
        if ns_uri in self.namespace_array:
            return
        self.namespace_array.append(ns_uri)

    #! SLOP ZONE
    #TODO Fix this function and add tests for it
    # def index_child_edge(self, parent: Node, child: Node):
    #     p = parent.minted_idx
    #     q = child.browse_name
    #     c = child.minted_idx
    #     self.child_index.setdefault(p, {}).setdefault(q, []).append(c)

    #TODO Fix this function and add tests for it
    # def child_by_qname(self, parent: Node, qname: QualifiedName, handle_multiple: str = "fail"):
    #     """handle_multiple: strategy used when model has not been properly build and multiple
    #     children have the same qualified name.
    #     Options:
    #         - fail: raises AmbiguousChildError
    #         - ignore: returns a list of matching nodes"""
    #     bucket = self.child_index.get(parent.minted_idx, {})
    #     indices = bucket.get(qname, [])
    #     if not indices:
    #         raise KeyError(qname)
    #     if len(indices) > 1:
    #         #log warning
    #         print(f"Warning: Multiple children found for {qname}. Make sure nodes have only a single child per qualified name.")
    #         if handle_multiple == "ignore":
    #             return [self.nodes_by_idx[idx] for idx in indices]
    #         else:
    #             raise AmbiguousChildError(qname)
    #     return self.nodes_by_idx(indices[0])

    def get_namespace_by_index(self, ns_idx: int) -> str:
        return self.namespace_array[ns_idx]

    def add_node(self, node: Node) -> None:
        self._mint_local_idx(node)
        self.ns_ctx._mint_global_idx(node)

        self.nid_to_idx[node.node_id] = node._local_idx

        # Browse name index
        self.nodes_by_browse_name.setdefault(node.browse_name, []).append(node)

        if not self.is_type_namespace:
            if node.node_class in node_definitions.TYPE_CLASSES:
                self.is_type_namespace = True

    def add_alias(self, alias: str, nid: str | NodeId) -> None:
        if isinstance(nid, str):
            nid = NodeId.from_string(nid)
        self.aliases[alias] = nid

    def find_by_nodeid(self, node_id: str | NodeId) -> Node | None:
        """ Finds a node by its NodeId. Returns None if the node does not exist.
        """
        if node_id is None:
            return None
        
        nid = node_id if isinstance(node_id, NodeId) else NodeId.from_string(node_id)

        local_idx = 0 if self.is_ua_namespace else 1
        if nid.ns_index == local_idx:
            idx = self.nid_to_idx.get(nid)
            return None if idx is None else self._find_by_idx(idx)

        return self.ns_ctx.resolve_node(nid, self)

    def find_by_browse_name(self, browse_name: str | QualifiedName) -> list[Node]:
        #TODO Clean this up
        if isinstance(browse_name, str):
            if self.is_ua_namespace:
                browse_name = QualifiedName.from_string(browse_name)
            else:
                browse_name = QualifiedName.from_string(browse_name, 1)
        return self.nodes_by_browse_name.get(browse_name, [])

#TODO Write new tests
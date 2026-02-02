from dataclasses import dataclass
from ua_nemo.node_definitions import NodeClass
from ua_nemo.types import NamespaceMetadata

# Minimal API stubs
class NodeIdStub:
    """
    Minimal NodeId:
    - to_string()
    - from_string()
    """
    __slots__ = ("_s",)

    def __init__(self, s: str):
        self._s = s

    @classmethod
    def from_string(cls, s: str) -> "NodeIdStub":
        s = (s or "").strip()
        # In tests, "i=..." and "ns=...;i=..." as "valid".
        # Anything empty is invalid to mimic parse failures.
        if not s:
            raise ValueError()
        return cls(s)

    def to_string(self) -> str:
        return self._s


@dataclass(frozen=True)
class RefStub:
    reference_type: NodeIdStub
    target_nodeid: NodeIdStub
    is_forward: bool


class NodeStub:
    """
    Minimal Node:
    - node_id (NodeIdStub)
    - references list containing objects with .reference_type/.target_nodeid/.is_forward
    - base_type for classification output
    """
    __slots__ = ("node_id", "browse_name", "node_class", "namespace", "attributes", "subnodes", "references", "base_type")

    def __init__(self, node_id_text, browse_name, node_class, namespace, attributes, subnodes):
        self.node_id = NodeIdStub.from_string(node_id_text)
        self.browse_name = browse_name
        self.node_class = node_class
        self.namespace = namespace
        self.attributes = attributes
        self.subnodes = subnodes
        self.references: list[RefStub] = []
        self.base_type = None

    def add_reference(self, reference_type, target_nodeid, is_forward):
        assert isinstance(reference_type, NodeIdStub), "reference_type must be NodeId"
        assert isinstance(target_nodeid, NodeIdStub), "target_nodeid must be NodeId"
        self.references.append(RefStub(reference_type, target_nodeid, is_forward))


class NamespaceStub:
    """
    - resolve(str|NodeId) -> NodeId
    - add_alias stores NodeId values
    - required model check uses namespace_context.namespace_dict_uri
    - find_by_nodeid used by _resolve_ua_basetype recursion
    """
    def __init__(self, loaded_model_uris: set[str] | None = None):
        self._loaded_model_uris = loaded_model_uris if loaded_model_uris is not None else set()

        self._uri = ""
        self.name = "MODEL"
        self.ns_info = {}
        self.aliases: dict[str, NodeIdStub] = {}
        self.nodes_by_id: dict[str, NodeStub] = {}
        self.namespace_context = type("Ctx", (), {"namespace_dict_uri": self._loaded_model_uris})()
        self.dependencies: list[NamespaceMetadata] = []

    @property
    def uri(self) -> str:
        return self._uri

    @uri.setter
    def uri(self, v: str):
        self._uri = v or ""
        if self._uri:
            # Treat loaded model URI as now known for RequiredModel checks
            self._loaded_model_uris.add(self._uri)

    def add_alias(self, alias_name, nodeid_text):
        if alias_name:
            self.aliases[alias_name] = NodeIdStub.from_string(nodeid_text or "")

    def resolve(self, nodeid_or_alias):
        if isinstance(nodeid_or_alias, NodeIdStub):
            return nodeid_or_alias

        # Alias?
        if nodeid_or_alias in self.aliases:
            return self.aliases[nodeid_or_alias]

        # NodeId literal?
        try:
            return NodeIdStub.from_string(nodeid_or_alias)
        except Exception:
            raise ValueError(f"Unknown alias or bad NodeId: {nodeid_or_alias}")

    def add_namespace(self, uri: str):
        if uri:
            self._loaded_model_uris.add(uri)

    def add_node(self, node: NodeStub):
        self.nodes_by_id[node.node_id.to_string()] = node

    def find_by_nodeid(self, nodeid: NodeIdStub):
        return self.nodes_by_id.get(nodeid.to_string())


def resolve_node_class_stub(tag: str):
    return NodeClass.ReferenceType if tag == "UAReferenceType" else NodeClass.Object


def split_node_fields_stub(node_class, raw: dict):
    # simplest: treat everything as attributes
    return raw, {}


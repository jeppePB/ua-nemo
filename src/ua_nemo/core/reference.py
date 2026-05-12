from ua_nemo.core.node_id import NodeId
from ua_nemo.types._protocols import NodeLike

class Reference:
    """
    target_idx references the minted index for the Node. It is populated if the node the reference is pointing from
    is in the same namespace as the node it is pointing to.
    """
    __slots__ = ("reference_type", "target_nodeid", "is_forward", "source", "target_idx")
    reference_type: NodeId
    source: NodeLike
    source_id: NodeId
    target_nodeid: NodeId
    is_forward: bool

    target_idx: int | None

    def __repr__(self) -> str:
        cls = self.__class__.__name__
        return (f"{cls}("
                f"type={self.reference_type!r}, "
                f"target={self.target_nodeid}, "
                f"is_forward={self.is_forward})")

    def __str__(self) -> str:
        direction = "->" if self.is_forward else "<-"
        return f"{self.reference_type} {direction} {self.target_nodeid}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Reference):
            return NotImplemented
        return (
            self.source is other.source
            and self.reference_type == other.reference_type
            and self.target_nodeid == other.target_nodeid
            and self.is_forward == other.is_forward
    )

    def __init__(self, reference_type: str|NodeId, target_nodeid: str|NodeId, is_forward:bool, source:NodeLike):
        if source.namespace:
            reference_type = source.namespace.resolve(reference_type)
        if not isinstance(target_nodeid, NodeId):
            target_nodeid = NodeId.from_string(target_nodeid)
        self.target_nodeid = target_nodeid
        self.is_forward = is_forward
        self.source = source
        self.reference_type = reference_type
        self.target_idx = None

    @property
    def is_hierarchical(self) -> bool:
        # Only hierarchical refs have base type for now
        ref_node = self.get_base_type_node()
        return ref_node.base_type is not None

    @property
    def base_type(self) -> str:
        ref_node = self.get_base_type_node()
        if ref_node is None:
            return None
        return ref_node.display_name

    @property
    def target(self) -> NodeLike:
        return self.source.namespace.find_by_nodeid(self.target_nodeid)

    def get_base_type_node(self) -> NodeLike:
        if not self.source.namespace:
            return None
        if not isinstance(self.reference_type, NodeId):
            self.reference_type = self.source.namespace.resolve(self.reference_type)
        return self.source.namespace.find_by_nodeid(self.reference_type)

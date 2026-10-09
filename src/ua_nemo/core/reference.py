from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ua_nemo.core.node_id import NodeId

if TYPE_CHECKING:
    from ua_nemo.core.node import Node

logger = logging.getLogger(__name__)

class Reference:
    """
    target_idx references the minted index for the Node. It is populated if the node the reference is pointing from
    is in the same namespace as the node it is pointing to.
    """
    __slots__ = ("_reference_type", "_warned_unresolved", "target_nodeid", "is_forward", "source", "target_idx")
    _reference_type: NodeId | str
    _warned_unresolved: bool
    source: Node
    source_id: NodeId
    target_nodeid: NodeId
    is_forward: bool

    target_idx: int | None

    def __repr__(self) -> str:
        cls = self.__class__.__name__
        return (f"{cls}("
                f"type={self._reference_type!r}, "
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
            and self._reference_type == other._reference_type
            and self.target_nodeid == other.target_nodeid
            and self.is_forward == other.is_forward
    )

    def __init__(self, reference_type: str|NodeId, target_nodeid: str|NodeId, is_forward:bool, source:Node):
        if not isinstance(target_nodeid, NodeId):
            target_nodeid = NodeId.from_string(target_nodeid)

        self.target_nodeid = target_nodeid
        self.is_forward = is_forward
        self.source = source
        self._reference_type = reference_type
        self._warned_unresolved = False
        self.target_idx = None

    @property
    def reference_type(self) -> NodeId | str:
        """A str is an unresolved alias. It is resolved on first access once the source node has a namespace,
        and stays a str if it can't be resolved."""
        if isinstance(self._reference_type, str) and self.source.namespace:
            try:
                self._reference_type = self.source.namespace.resolve(self._reference_type)
            except ValueError:
                if not self._warned_unresolved:
                    self._warned_unresolved = True
                    logger.warning("Could not resolve reference type '%s'. Keeping the raw value.", self._reference_type)
        return self._reference_type

    @property
    def is_hierarchical(self) -> bool:
        # Only hierarchical refs have base type for now
        ref_node = self.get_base_type_node()
        if ref_node is None:
            return False
        return ref_node.base_type is not None

    @property
    def base_type(self) -> str | None:
        ref_node = self.get_base_type_node()
        if ref_node is None:
            return None
        return ref_node.display_name

    @property
    def target(self) -> Node | None:
        return self.source.namespace.find_by_nodeid(self.target_nodeid)

    def get_base_type_node(self) -> Node | None:
        if not self.source.namespace:
            return None
        ref_type = self.reference_type
        if not isinstance(ref_type, NodeId):
            return None
        return self.source.namespace.find_by_nodeid(ref_type)

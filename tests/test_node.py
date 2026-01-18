import pytest

import ua_nemo.node_model as nm
from ua_nemo.node_definitions import NodeClass

class FakeNamespace:
    def __init__(self, uri="urn:example"):
        self.uri = uri
        self._nodes = {}
        self._resolve_map = {}

    def register(self, nodeid, node):
        self._nodes[nodeid] = node

    def find_by_nodeid(self, nodeid):
        return self._nodes.get(nodeid)

    def resolve(self, reference_type):
        return self._resolve_map.get(reference_type, reference_type)


class FakeReference:
    def __init__(self, reference_type, target_nodeid, is_forward=True, source=None):
        self.reference_type = reference_type
        self.target_nodeid = target_nodeid
        self.is_forward = is_forward
        self.source = source

    def __eq__(self, other):
        return (
            isinstance(other, FakeReference)
            and self.reference_type == other.reference_type
            and self.target_nodeid == other.target_nodeid
            and self.is_forward == other.is_forward
        )


@pytest.fixture
def ns():
    return FakeNamespace(uri="urn:example")

def test_create_node_str_nid(ns):
    node_id = 'ns=1;s=test'

    node = nm.Node(node_id, "test", NodeClass.Object, ns)

    assert isinstance(node.node_id, nm.NodeId)
    assert node.node_id.to_string() == node_id

def test_create_node_nid_object(ns):
    node_id = nm.NodeId.from_string('ns=1;s=test')

    node = nm.Node(node_id, 'test', NodeClass.Object, ns)

    assert isinstance(node.node_id, nm.NodeId)
    assert node.node_id == node_id


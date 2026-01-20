import pytest
import types

import ua_nemo.node_model as nm
import ua_nemo.node_definitions as ndef

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
def ns() -> FakeNamespace:
    return FakeNamespace(uri="urn:example")


def test_create_node_nid_object(ns):
    nid = nm.NodeId.from_string('ns=1;s=test')

    n = nm.Node(nid, 'test', ndef.NodeClass.Object, ns)

    assert isinstance(n.node_id, nm.NodeId)
    assert n.node_id == nid
    assert n.is_object is True
    assert n.is_variable is False

def test_create_node_str_nid(ns):
    nid = 'ns=1;s=test'

    n = nm.Node(nid, "test", ndef.NodeClass.Object, ns)

    assert isinstance(n.node_id, nm.NodeId)
    assert n.node_id.to_string() == nid

def test_display_name_defaulted(ns):
    n = nm.Node('ns=1;s=1234', 'test', ndef.NodeClass.Object, ns)
    assert n.display_name == 'test'
    assert n.subnodes['DisplayName'] == 'test'

def test_node_uri(ns):
    n = nm.Node('ns=1;s=1234', 'test', ndef.NodeClass.Object, ns)
    
    assert n.node_uri.startswith('urn:example#')

def test_type_definition_picks_i40(ns):
    n = nm.Node("ns=1;i=1", "1:Foo", ndef.NodeClass.Object, ns)
    n.references.append(FakeReference("i=40", "ns=1;i=999", True, n))
    assert n.type_definition == "ns=1;i=999"

def test_type_uri_prefers_found_type_node(ns):
    type_node = nm.Node("ns=1;i=999", "1:MyType", ndef.NodeClass.ObjectType, ns)
    ns.register("ns=1;i=999", type_node)

    n = nm.Node("ns=1;i=1", "1:Foo", ndef.NodeClass.Object, ns)
    n.references.append(FakeReference("i=40", "ns=1;i=999", True, n))

    assert n.type_uri == "urn:example#MyType"

def test_type_uri_falls_back_to_self_when_abstract_and_type_missing(ns, monkeypatch):
    monkeypatch.setattr(
        nm,
        "node_definitions",
        types.SimpleNamespace(TYPE_CLASSES={nm.NodeClass.ObjectType, nm.NodeClass.VariableType}),
    )
    n = nm.Node("ns=1;i=10", "AbstractType", nm.NodeClass.ObjectType, ns)
    assert n.type_uri == "urn:example#AbstractType"

def test_hierarchical_children_parents(ns):
    # Create a hierarchical ref-type node. For it to count as hierarchical in the current logic in
    # get_hierarchical_references it needs to have the base_type set (to literally anything at all)
    ref_type_node = nm.Node("i=200", "1:HasComponent", ndef.NodeClass.ReferenceType, ns)
    ref_type_node.base_type = nm.NodeId.from_string("ns=0;i=33")
    ns.register("i=200", ref_type_node)
    ns._resolve_map["i=200"] = "i=200"

    n = nm.Node("ns=1;i=1", "1:Foo", ndef.NodeClass.Object, ns)
    fwd = FakeReference("i=200", "ns=1;i=2", True, n)
    bwd = FakeReference("i=200", "ns=1;i=3", False, n)
    n.references.extend([fwd, bwd])

    assert n.hierarchical_children == [fwd]
    assert n.hierarchical_parents == [bwd]

def test_add_reference_dedup(ns, monkeypatch):
    monkeypatch.setattr(nm, "Reference", FakeReference)

    n = nm.Node("ns=1;i=1", "1:Foo", ndef.NodeClass.Object, ns)
    n.add_reference("i=200", "ns=1;i=2", True)
    n.add_reference("i=200", "ns=1;i=2", True)
    assert len(n.references) == 1

def test_property_is_object_is_variable(ns):
    o = nm.Node("ns=1;i=1", "Obj", ndef.NodeClass.Object, ns)
    v = nm.Node("ns=1;i=2", "Var", ndef.NodeClass.Variable, ns)
    assert o.is_object is True
    assert o.is_variable is False
    assert v.is_object is False
    assert v.is_variable is True

def test_property_is_abstract_uses_type_classes(ns, monkeypatch):
    # Control the rule set for a stable test
    monkeypatch.setattr(
        nm,
        "node_definitions",
        types.SimpleNamespace(TYPE_CLASSES={ndef.NodeClass.ObjectType, ndef.NodeClass.VariableType}),
    )
    t = nm.Node("ns=1;i=10", "Type", ndef.NodeClass.ObjectType, ns)
    assert t.is_abstract is True
import types
import pytest
import logging

from ua_nemo.core import NodeId, Node
import ua_nemo.core.node as node_module
import ua_nemo.node_definitions as ndef


def test_create_node_nid_object(ns):
    nid = NodeId.from_string('ns=1;s=test')
    n = Node(nid, 'test', ndef.NodeClass.Object, ns)
    assert isinstance(n.node_id, NodeId)
    assert n.node_id == nid
    assert n.is_object is True
    assert n.is_variable is False


def test_create_node_str_nid(ns):
    nid = 'ns=1;s=test'
    n = Node(nid, "test", ndef.NodeClass.Object, ns)
    assert isinstance(n.node_id, NodeId)
    assert n.node_id.to_string() == nid


def test_display_name_defaulted(ns):
    n = Node('ns=1;s=1234', 'test', ndef.NodeClass.Object, ns)
    assert n.display_name == 'test'
    assert n.subnodes['DisplayName'] == 'test'


def test_node_uri(ns):
    n = Node('ns=1;s=1234', 'test', ndef.NodeClass.Object, ns)
    assert n.node_uri.startswith('urn:example#')


def test_type_definition_picks_i40(ns, make_ref):
    n = Node("ns=1;i=1", "1:Foo", ndef.NodeClass.Object, ns)
    n.references.append(make_ref(NodeId.from_string("i=40"), "ns=1;i=999", True, n))
    assert n.type_definition == NodeId.from_string("ns=1;i=999")


def test_type_uri_prefers_found_type_node(ns, make_ref):
    type_node = Node("ns=1;i=999", "1:MyType", ndef.NodeClass.ObjectType, ns)
    ns.add_node(type_node)

    n = Node("ns=1;i=1", "1:Foo", ndef.NodeClass.Object, ns)
    n.references.append(make_ref(NodeId.from_string("i=40"), "ns=1;i=999", True, n))

    assert n.type_uri == "urn:example#MyType"


def test_type_uri_falls_back_to_self_when_abstract_and_type_missing(ns):
    n = Node("ns=1;i=10", "AbstractType", ndef.NodeClass.ObjectType, ns)
    assert n.type_uri == "urn:example#AbstractType"

def test_type_uri_returns_none_for_non_abstract_missing_type(ns, caplog):
    # Object node, no HasTypeDefinition (i=40) reference, not abstract.
    n = Node("ns=1;i=1", "Orphan", ndef.NodeClass.Object, ns)
    with caplog.at_level(logging.WARNING):
        result = n.type_uri

    assert result is None
    assert len(caplog.records) == 1
    assert caplog.records[0].levelno == logging.WARNING

def test_hierarchical_children_parents(ns, make_ref):
    ref_type_node = Node("ns=1;i=200", "1:HasComponent", ndef.NodeClass.ReferenceType, ns)
    ref_type_node.base_type = NodeId.from_string("ns=0;i=33")
    ns.add_node(ref_type_node)

    n = Node("ns=1;i=1", "1:Foo", ndef.NodeClass.Object, ns)
    fwd = make_ref("ns=1;i=200", "ns=1;i=2", True, n)
    bwd = make_ref("ns=1;i=200", "ns=1;i=3", False, n)
    n.references.extend([fwd, bwd])

    assert n.hierarchical_children == [fwd]
    assert n.hierarchical_parents == [bwd]

def test_hierarchical_references_skip_unresolvable_reference_type(ns, make_ref):
    n = Node("ns=1;i=1", "1:Foo", ndef.NodeClass.Object, ns)
    n.references.append(make_ref("NotAnAlias", "ns=1;i=2", True, n))

    assert n.hierarchical_children == []
    assert n.hierarchical_parents == []

def test_add_reference_dedup(ns):
    n = Node("ns=1;i=1", "1:Foo", ndef.NodeClass.Object, ns)
    n.add_reference("ns=1;i=200", "ns=1;i=2", True)
    n.add_reference("ns=1;i=200", "ns=1;i=2", True)
    assert len(n.references) == 1


def test_property_is_object_is_variable(ns):
    o = Node("ns=1;i=1", "Obj", ndef.NodeClass.Object, ns)
    v = Node("ns=1;i=2", "Var", ndef.NodeClass.Variable, ns)
    assert o.is_object is True
    assert o.is_variable is False
    assert v.is_object is False
    assert v.is_variable is True


def test_property_is_abstract_uses_type_classes(ns, monkeypatch):
    monkeypatch.setattr(
        node_module, "nd",
        types.SimpleNamespace(TYPE_CLASSES={ndef.NodeClass.ObjectType, ndef.NodeClass.VariableType}),
    )
    t = Node("ns=1;i=10", "Type", ndef.NodeClass.ObjectType, ns)
    assert t.is_abstract is True
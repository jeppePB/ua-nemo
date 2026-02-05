import types

import ua_nemo.node_model as nm
from ua_nemo.core import NodeId
import ua_nemo.node_definitions as ndef

def test_create_node_nid_object(ns):
    nid = NodeId.from_string('ns=1;s=test')

    n = nm.Node(nid, 'test', ndef.NodeClass.Object, ns)

    assert isinstance(n.node_id, NodeId)
    assert n.node_id == nid
    assert n.is_object is True
    assert n.is_variable is False

def test_create_node_str_nid(ns):
    nid = 'ns=1;s=test'

    n = nm.Node(nid, "test", ndef.NodeClass.Object, ns)

    assert isinstance(n.node_id, NodeId)
    assert n.node_id.to_string() == nid

def test_display_name_defaulted(ns):
    n = nm.Node('ns=1;s=1234', 'test', ndef.NodeClass.Object, ns)
    assert n.display_name == 'test'
    assert n.subnodes['DisplayName'] == 'test'

def test_node_uri(ns):
    n = nm.Node('ns=1;s=1234', 'test', ndef.NodeClass.Object, ns)
    
    assert n.node_uri.startswith('urn:example#')

def test_type_definition_picks_i40(ns, fake_ref):
    n = nm.Node("ns=1;i=1", "1:Foo", ndef.NodeClass.Object, ns)
    n.references.append(fake_ref(NodeId.from_string("i=40"), "ns=1;i=999", True, n))
    assert n.type_definition == "ns=1;i=999"

def test_type_uri_prefers_found_type_node(ns, fake_ref):
    type_node = nm.Node("ns=1;i=999", "1:MyType", ndef.NodeClass.ObjectType, ns)
    ns.register("ns=1;i=999", type_node)

    n = nm.Node("ns=1;i=1", "1:Foo", ndef.NodeClass.Object, ns)
    n.references.append(fake_ref(NodeId.from_string("i=40"), "ns=1;i=999", True, n))

    assert n.type_uri == "urn:example#MyType"

def test_type_uri_falls_back_to_self_when_abstract_and_type_missing(ns, monkeypatch):
    monkeypatch.setattr(
        nm,
        "node_definitions",
        types.SimpleNamespace(TYPE_CLASSES={nm.NodeClass.ObjectType, nm.NodeClass.VariableType}),
    )
    n = nm.Node("ns=1;i=10", "AbstractType", nm.NodeClass.ObjectType, ns)
    assert n.type_uri == "urn:example#AbstractType"

def test_hierarchical_children_parents(ns, fake_ref):
    # Create a hierarchical ref-type node. For it to count as hierarchical in the current logic in
    # get_hierarchical_references it needs to have the base_type set (to literally anything at all)
    ref_type_node = nm.Node("i=200", "1:HasComponent", ndef.NodeClass.ReferenceType, ns)
    ref_type_node.base_type = NodeId.from_string("ns=0;i=33")
    ns.register("i=200", ref_type_node)
    ns._resolve_map["i=200"] = "i=200"

    n = nm.Node("ns=1;i=1", "1:Foo", ndef.NodeClass.Object, ns)
    fwd = fake_ref("i=200", "ns=1;i=2", True, n)
    bwd = fake_ref("i=200", "ns=1;i=3", False, n)
    n.references.extend([fwd, bwd])

    assert n.hierarchical_children == [fwd]
    assert n.hierarchical_parents == [bwd]

def test_add_reference_dedup(ns, monkeypatch, fake_ref):
    monkeypatch.setattr(nm, "Reference", fake_ref)

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
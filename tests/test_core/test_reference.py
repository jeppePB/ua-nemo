import pytest
from unittest.mock import MagicMock

from ua_nemo.core import Reference, Node, NodeId
from ua_nemo.node_definitions import NodeClass

@pytest.fixture(autouse=True, scope="function")
def add_alias(ns):
    ns.register_alias("Organizes", NodeId.from_string("i=40"))

def test_init_converts_string_to_nodeid(ns):
    src = Node("i=1", "test", NodeClass.Object, ns)
    r = Reference(reference_type="i=40", target_nodeid="ns=1;i=123", is_forward=True, source=src)

    assert isinstance(r.target_nodeid, NodeId)
    assert r.is_forward is True
    assert r.source is src

def test_init_converts_alias_to_nodeid_if_namespace(ns):
    src = Node("i=1", "test", NodeClass.Object, ns)
    r = Reference(reference_type="Organizes", target_nodeid="ns=1;i=123", is_forward=True, source=src)

    assert isinstance(r.target_nodeid, NodeId)
    assert isinstance(r.reference_type, NodeId)
    assert r.is_forward is True
    assert r.source is src

def test_init_leaves_alias_as_is_if_no_namespace(ns):
    src = Node("i=1", "test", NodeClass.Object, None)
    r = Reference(reference_type="Organizes", target_nodeid="ns=1;i=123", is_forward=True, source=src)

    assert r.reference_type == "Organizes"
    assert isinstance(r.target_nodeid, NodeId)
    assert r.is_forward is True
    assert r.source is src

def test_init_accepts_target_nodeid_as_nodeid_without_conversion(ns):
    src = Node("i=1", "test", NodeClass.Object, namespace=ns)
    nid = NodeId.from_string("ns=2;s=SomeId")

    r = Reference(reference_type="Organizes", target_nodeid=nid, is_forward=False, source=src)

    assert r.target_nodeid is nid  # same object
    assert r.is_forward is False


def test_str_forward_and_backward(ns):
    src = Node("i=1", "test", NodeClass.Object, namespace=ns)

    r_fwd = Reference("Organizes", "ns=0;i=40", True, src)
    assert str(r_fwd) == "ns=0;i=40 -> ns=0;i=40"

    r_bwd = Reference("Organizes", "ns=0;i=40", False, src)
    assert str(r_bwd) == "ns=0;i=40 <- ns=0;i=40"


def test_target_property_calls_namespace_find_by_nodeid_with_target_nodeid(ns):
    src = Node("i=1", "test", NodeClass.Object, namespace=ns)
    ns.find_by_nodeid = MagicMock()

    expected_target = object()
    ns.find_by_nodeid.return_value = expected_target

    r = Reference("Organizes", "ns=3;i=9", True, src)
    got = r.target

    ns.find_by_nodeid.assert_called_once_with(NodeId.from_string("ns=3;i=9"))
    assert got is expected_target


def test_get_base_type_node_does_not_resolve_if_reftype_is_nodeid(ns):
    src = Node("i=1", "test", NodeClass.Object, namespace=ns)

    ns.resolve = MagicMock()
    ns.find_by_nodeid = MagicMock()

    resolved_nid = NodeId.from_string("ns=0;i=35")
    ns.resolve.return_value = resolved_nid

    ref_type_node = Node("i=48", "HierarchicalReferences", NodeClass.ReferenceType, ns)
    ns.find_by_nodeid.return_value = ref_type_node

    r = Reference("Organizes", "ns=1;i=1", True, src)
    got = r.get_base_type_node()

    ns.resolve.assert_called_once_with("Organizes")
    ns.find_by_nodeid.assert_called_once_with(resolved_nid)
    assert got is ref_type_node

def test_get_base_type_node_resolves_reference_type_then_finds_node(ns):
    src = Node("i=1", "test", NodeClass.Object, None)

    ns.resolve = MagicMock()
    ns.find_by_nodeid = MagicMock()

    resolved_nid = NodeId.from_string("ns=0;i=35")
    ns.resolve.return_value = resolved_nid

    ref_type_node = Node("i=48", "HierarchicalReferences", NodeClass.ReferenceType, ns)
    ns.find_by_nodeid.return_value = ref_type_node

    r = Reference("Organizes", "ns=1;i=1", True, src)
    ns.resolve.assert_not_called()

    src.namespace = ns
    got = r.get_base_type_node()

    ns.resolve.assert_called_once_with("Organizes")
    ns.find_by_nodeid.assert_called_once_with(resolved_nid)
    assert got is ref_type_node

def test_get_base_type_returns_none_if_namespace_if_none():
    src = Node("i=1", "test", NodeClass.Object, None)
    r = Reference("Organizes", "ns=1;i=1", True, src)

    assert r.get_base_type_node() is None


def test_is_hierarchical_true_when_base_type_is_not_none(ns):
    ref_node = Node("i=40", "Organizes", NodeClass.ReferenceType, ns)
    ref_node.base_type = True

    ns.register(ref_node.node_id, node=ref_node)
    
    src = Node("i=1", "test", NodeClass.Object, namespace=ns)
    
    r = Reference("Organizes", "ns=1;i=1", True, src) 

    assert r.is_hierarchical is True

def test_is_hierarchical_false_when_base_type_is_none(ns):
    ref_node = Node("i=40", "Organizes", NodeClass.ReferenceType, ns)
    ref_node.base_type = None
    
    ns.register(ref_node.node_id, node=ref_node)
    
    src = Node("i=1", "test", NodeClass.Object, namespace=ns)
    
    r = Reference("Organizes", "ns=1;i=1", True, src) 

    assert r.is_hierarchical is False


def test_base_type_returns_display_name_from_base_type_node(ns):
    ref_node = Node("i=40", "Organizes", NodeClass.ReferenceType, ns)
    ref_node.base_type = True

    # ns.register(base_type.node_id, node=base_type)
    ns.register(ref_node.node_id, node=ref_node)
    
    src = Node("i=1", "test", NodeClass.Object, namespace=ns)
    
    # make get_base_type_node() return a "ref type" node with base_type not None
    r = Reference("Organizes", "ns=1;i=1", True, src) 


    assert r.base_type == ref_node.display_name
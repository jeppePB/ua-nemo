import pytest
import logging

from ua_nemo.node_model import (
    NamespaceContext, 
)
from ua_nemo.node_definitions import NodeClass
from ua_nemo.core import NodeId, Node, Namespace

def test_create_namespace_defaults(ctx):
    ns = Namespace(ctx)

    assert isinstance(ns.namespace_context, NamespaceContext)
    assert ns.name is None
    assert ns.uri is None

def test_uri_cannot_be_overwritten(caplog, ctx):
    ns = Namespace(ctx)
    ns.uri = "http://yourcompany.com/test-types/"
    with caplog.at_level(logging.WARNING):
        ns.uri = "thisfails"
    
    assert len(caplog.records) == 1
    assert ns.uri in caplog.text.lower() and "thisfails" in caplog.text.lower()

def test_set_uri_name_from_url_path(ctx):
    ns = Namespace(ctx)
    ns_two = Namespace(ctx)
    ns.uri = "http://yourcompany.com/test-types/"
    ns_two.uri = "http://yourcompany.com/test-types/test"
    assert ns.name == "test-types"
    assert ns_two.name == "test-types_test"

def test_set_uri_name_from_non_url(ctx):
    ns = Namespace(ctx)
    ns.uri = "urn:my-types/"
    assert ns.name == "my-types"


def test_set_uri_none_is_error(ctx):
    ns = Namespace(ctx)
    with pytest.raises(ValueError):
        ns.uri = None
    assert ns.uri is None
    assert ns.name is None

def test_resolve_returns_nodeid_unchanged(ctx):
    ns = Namespace(ctx)
    nid = NodeId.from_string("ns=1;i=123")
    assert ns.resolve(nid) is nid

def test_resolve_alias_takes_precedence_over_parsing(ctx):
    ns = Namespace(ctx)
    ns.add_alias("MyAlias", "i=63")
    assert ns.resolve("MyAlias") == NodeId.from_string("ns=0;i=63")

def test_resolve_parses_nodeid_string(ctx):
    ns = Namespace(ctx)
    nid = ns.resolve("ns=1;i=123")
    assert isinstance(nid, NodeId)
    assert nid.to_string() == NodeId.from_string("ns=1;i=123").to_string()

def test_resolve_unknown_alias_raises_valueerror(ctx):
    ns = Namespace(ctx)
    with pytest.raises(ValueError):
        ns.resolve("NotAnAliasAndNotANodeId")

def test_add_alias_expanded_form(ctx):
    ns = Namespace(ctx)
    ns.add_alias("Alias1", "ns=2;i=10")
    assert ns.aliases["Alias1"] == NodeId.from_string("ns=2;i=10")

def test_add_alias_short_form_defaults_to_ns0(ctx):
    ns = Namespace(ctx)
    ns.add_alias("Alias2", "i=63")
    assert ns.aliases["Alias2"] == NodeId.from_string("ns=0;i=63")

def test_add_namespace_dedup_and_index(ctx):
    ns = Namespace(ctx)
    ns.add_namespace("urn:one")
    ns.add_namespace("urn:one")
    ns.add_namespace("urn:two")

    assert ns.namespace_array == ["urn:one", "urn:two"]
    assert ns.get_namespace_by_index(1) == "urn:two"

def test_add_node_indexes_by_id_and_browse_name(ctx):
    # Ensure ns has a URI so Node.node_uri logic won't break if referenced elsewhere
    ns = Namespace(ctx)
    ns.uri = "urn:example"

    node = Node(
        node_id=NodeId.from_string("ns=1;i=1"),
        browse_name="1:Foo",
        node_class=NodeClass.Object,
        namespace=ns
    )

    ns.add_node(node)

    assert node.node_id.to_string() in ns.nodes_by_id
    assert ns.nodes_by_id[node.node_id.to_string()] is node
    assert ns.find_by_browse_name("Foo") == [node]

def test_add_node_sets_is_type_namespace_when_type_class_added(ctx):
    # TODO Monkeypatch type classes just in case
    ns = Namespace(ctx)
    ns.uri = "urn:example"

    type_node = Node("ns=1;i=100", "1:MyType", NodeClass.ObjectType, ns)
    ns.add_node(type_node)

    assert ns.is_type_namespace is True

def test_find_by_nodeid_local_ns1(ctx):
    ns = Namespace(ctx)
    ns.uri = "urn:model1"

    node = Node("ns=1;i=1", "1:Foo", NodeClass.Object, ns)
    ns.add_node(node)

    found = ns.find_by_nodeid("ns=1;i=1")
    assert found is node

def test_find_by_nodeid_ua_model_ns0_local(ctx):
    ua = Namespace(ctx)
    ua.uri = "http://opcfoundation.org/UA/"  # any URI; name matters
    ua.name = "UA"

    node = Node("ns=0;i=84", "0:Root", NodeClass.Object, ua)
    ua.add_node(node)

    found = ua.find_by_nodeid("ns=0;i=84")
    assert found is node

def test_find_by_nodeid_ns0_delegates_to_ua_model(ctx):
    ua = Namespace(ctx)
    ua.name = "UA"
    ua.uri = "urn:UA"

    ua_node = Node("ns=0;i=84", "0:Root", NodeClass.Object, ua)
    ua.add_node(ua_node)

    model = Namespace(ctx)
    model.uri = "urn:model1"

    found = model.find_by_nodeid("ns=0;i=84")
    assert found is ua_node

def test_find_by_nodeid_other_namespace_normalizes_to_ns1(ctx):
    """
    All nodes returned by find_by_nodeid get their ns normalized to 1 (except UA)
    Add a test to make sure this behavior is consistent until a change is desired."""
    #Empty ua namespace to fill ns0
    ua = Namespace(ctx)
    ua.uri = "urn:UA"
    
    target = Namespace(ctx)
    target.uri = "urn:target"

    # Node stored locally in target model with ns=1
    target_node_ns_string = "ns=1;i=500"
    target_node = Node(target_node_ns_string, "1:Thing", NodeClass.Object, target)
    target.add_node(target_node)

    source = Namespace(ctx)
    source.uri = "urn:source"
    source.add_namespace(target.uri)

    # Ask source for ns=2;i=500, should be normalized to ns=1;i=500 in target
    found = source.find_by_nodeid("ns=2;i=500")
    assert found is target_node
    assert found.node_id.to_string() == target_node_ns_string

def test_find_by_browse_name_normalizes_for_non_ua(ctx):
    ns = Namespace(ctx)
    ns.uri = "urn:model1"
    ns.name = "Model1"

    node = Node("ns=1;i=1", "1:Foo", NodeClass.Object, ns)
    ns.add_node(node)

    # Ask without "1:" prefix
    assert ns.find_by_browse_name("Foo") == [node]

def test_find_by_browse_name_does_not_normalize_for_ua(ctx):
    ua = Namespace(ctx)
    ua.uri = "urn:UA"
    ua.name = "UA"

    node = Node("ns=0;i=84", "0:Root", NodeClass.Object, ua)
    ua.add_node(node)

    # For UA model, don't force "1:" prefix
    assert ua.find_by_browse_name("0:Root") == [node]

def test_node_is_assigned_minted_idx(ctx):
    ns = Namespace(ctx)
    ns.uri = "urn:model1"

    node = Node("ns=1;i=1", "1:Foo", NodeClass.Object, ns)
    assert node.minted_idx is None
    ns.add_node(node)
    assert node.minted_idx == 0
    assert ns._next_node_idx == 1
    
    node_two = Node("ns=1;i=100", "1:Foo", NodeClass.Object, ns)
    assert node_two.minted_idx is None
    ns.add_node(node_two)
    assert node_two.minted_idx == 1
    assert ns._next_node_idx == 2

def test_node_is_assigned_minted_idx_per_ns(ctx):
    ns = Namespace(ctx)
    ns.uri = "urn:model1"
    ns_2 = Namespace(ctx)
    ns_2.uri = "urn:model2"

    node = Node("ns=1;i=1", "1:Foo", NodeClass.Object, ns)
    node_2 = Node("ns=1;i=1", "1:Foo", NodeClass.Object, ns_2)
    node_3 = Node("ns=1;i=1", "1:Foo", NodeClass.Object, ns_2)
    
    ns.add_node(node)
    ns_2.add_node(node_2)
    ns_2.add_node(node_3)

    # Index should only count up on a per-namespace basis
    assert ns._next_node_idx == 1
    assert ns_2._next_node_idx == 2
    # Node should be assigned correct index
    assert node_3.minted_idx == 1

def test_find_node_by_idx(ctx):
    ns = Namespace(ctx)
    ns.uri = "urn:model1"

    node = Node("ns=1;i=1", "1:Foo", NodeClass.Object, ns)
    ns.add_node(node)

    assert ns.find_by_idx(0) == node

def test_find_node_by_nodeid(ctx):
    #TODO Replace og find_by_nodeid
    ns = Namespace(ctx)
    ns.uri = "urn:model1"

    node = Node("ns=1;i=1", "1:Foo", NodeClass.Object, ns)
    ns.add_node(node)

    assert ns.find_by_nodeid("ns=1;i=1") == node

    nid = NodeId.from_string("ns=1;i=1")
    assert ns.find_by_nodeid(nid) == node

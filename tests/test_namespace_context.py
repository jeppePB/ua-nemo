from __future__ import annotations

import pytest

from ua_nemo.core.namespace import (
    Namespace,
    NamespaceContext,
    Node,
    NodeId)
from ua_nemo.node_definitions import NodeClass


UA_URI = "http://opcfoundation.org/UA/"


def make_node(node_id: str, browse_name: str, namespace: Namespace,
              node_class: NodeClass = NodeClass.Object) -> Node:
    return Node(node_id, browse_name, node_class, namespace)


def register_model(ctx: NamespaceContext, uri: str) -> Namespace:
    ns = Namespace(namespace_context=ctx)
    ns.uri = uri  # setter triggers ctx.register_model(ns)
    return ns


@pytest.fixture
def ctx() -> NamespaceContext:
    return NamespaceContext()


@pytest.fixture
def ua_namespace(ctx) -> Namespace:
    return register_model(ctx, UA_URI)


# ---- empty() ----

def test_empty_true_for_fresh_context(ctx):
    assert ctx.empty() is True


def test_empty_false_after_registering_a_model(ctx, ua_namespace):
    assert ctx.empty() is False


# ---- register_model ----

def test_register_model_indexes_by_name_and_uri(ctx, ua_namespace):
    assert ctx.get_namespace_by_name("UA") is ua_namespace
    assert ctx.get_namespace_by_uri(UA_URI) is ua_namespace


def test_ua_namespace_only_adds_itself_to_its_own_array(ua_namespace):
    assert ua_namespace.namespace_array == [UA_URI]


def test_dependent_model_gets_ua_at_index_zero_and_self_at_index_one(ctx, ua_namespace):
    custom = register_model(ctx, "urn:test:model1")
    assert custom.namespace_array == [UA_URI, "urn:test:model1"]


def test_register_model_warns_when_ua_not_yet_loaded(ctx, capsys):
    register_model(ctx, "urn:test:model1")
    assert "UA namespace has not been loaded" in capsys.readouterr().out


def test_own_uri_still_added_when_ua_missing(ctx):
    custom = register_model(ctx, "urn:test:model1")
    assert custom.namespace_array == ["urn:test:model1"]


# ---- get_model / get_model_by_uri ----

def test_get_model_requires_name_or_uri(ctx):
    with pytest.raises(ValueError):
        ctx.get_model()


def test_get_model_by_name(ctx, ua_namespace):
    assert ctx.get_model(name="UA") is ua_namespace


def test_get_model_by_uri_arg(ctx, ua_namespace):
    assert ctx.get_model(uri=UA_URI) is ua_namespace


def test_get_model_returns_none_for_unknown_name(ctx, ua_namespace):
    assert ctx.get_model(name="nope") is None


def test_get_model_returns_none_for_unknown_uri(ctx, ua_namespace):
    assert ctx.get_model(uri="urn:nope") is None


def test_get_model_by_uri_success(ctx, ua_namespace):
    assert ctx.get_namespace_by_uri(UA_URI) is ua_namespace


def test_get_model_by_uri_returns_none_for_unknown_uri(ctx):
    # Note: unlike get_model(uri=...), this indexes directly and raises rather than
    # returning None -- an existing inconsistency, tested here as current behavior.
    assert ctx.get_namespace_by_uri("urn:nope") is None


# ---- _get_ns_idx_relative_to_target ----

def test_get_ns_idx_relative_to_target_appends_new_uri(ctx):
    target = Namespace()
    idx = ctx._get_ns_idx_relative_to_target(target, "urn:foo")
    assert idx == 0
    assert target.namespace_array == ["urn:foo"]


def test_get_ns_idx_relative_to_target_dedupes_and_keeps_original_index(ctx):
    target = Namespace()
    ctx._get_ns_idx_relative_to_target(target, "urn:foo")
    ctx._get_ns_idx_relative_to_target(target, "urn:bar")
    idx = ctx._get_ns_idx_relative_to_target(target, "urn:foo")
    assert idx == 0
    assert target.namespace_array == ["urn:foo", "urn:bar"]


# ---- resolve_node ----

def test_resolve_node_finds_ua_node_from_dependent_model(ctx, ua_namespace):
    custom = register_model(ctx, "urn:test:model1")
    ua_node = make_node("ns=0;i=1", "0:SomeUAType", ua_namespace, NodeClass.ReferenceType)
    ua_namespace.add_node(ua_node)

    found = ctx.resolve_node(NodeId.from_string("ns=0;i=1"), from_ns=custom)
    assert found is ua_node


def test_resolve_node_finds_own_node_via_normalized_index(ctx, ua_namespace):
    custom = register_model(ctx, "urn:test:model1")
    own_node = make_node("ns=1;i=100", "1:CustomObject", custom)
    custom.add_node(own_node)

    found = ctx.resolve_node(NodeId.from_string("ns=1;i=100"), from_ns=custom)
    assert found is own_node


def test_resolve_node_across_two_dependent_models(ctx, ua_namespace):
    model_a = register_model(ctx, "urn:test:model_a")
    model_b = register_model(ctx, "urn:test:model_b")

    dep_idx = ctx._get_ns_idx_relative_to_target(model_a, model_b.uri)  # model_a learns of model_b

    b_node = make_node("ns=1;i=5", "1:SharedType", model_b)
    model_b.add_node(b_node)

    nid_from_a = NodeId.from_string(f"ns={dep_idx};i=5")
    found = ctx.resolve_node(nid_from_a, from_ns=model_a)
    assert found is b_node


def test_resolve_node_returns_none_for_unregistered_target_namespace(ctx, ua_namespace):
    model_a = register_model(ctx, "urn:test:model_a")
    model_a.add_namespace("urn:ghost:model")  # known to model_a, never registered with ctx
    ghost_idx = model_a.namespace_array.index("urn:ghost:model")

    result = ctx.resolve_node(NodeId.from_string(f"ns={ghost_idx};i=1"), from_ns=model_a)
    assert result is None


def test_resolve_node_ns0_returns_none_when_ua_not_loaded(ctx):
    # Without UA, index 0 of the model's array is the model itself, so this must not recurse.
    custom = register_model(ctx, "urn:test:model1")

    assert ctx.resolve_node(NodeId.from_string("ns=0;i=40"), from_ns=custom) is None


def test_find_by_nodeid_ns0_returns_none_when_ua_not_loaded(ctx):
    custom = register_model(ctx, "urn:test:model1")

    assert custom.find_by_nodeid("ns=0;i=40") is None


# ---- remap_nodeid ----

def test_remap_nodeid_reindexes_into_target_models_namespace_array(ctx, ua_namespace):
    from_model = register_model(ctx, "urn:test:from_model")
    to_model = register_model(ctx, "urn:test:to_model")

    dep_idx_in_from = ctx._get_ns_idx_relative_to_target(from_model, "urn:test:shared_dep")
    ctx._get_ns_idx_relative_to_target(to_model, "urn:test:unrelated")  # occupies index 2 in to_model

    nid = NodeId.from_string(f"ns={dep_idx_in_from};i=7")
    remapped = ctx.remap_nodeid(nid, from_model, to_model)

    # to_model's array so far: [UA(0), to_model itself(1), unrelated(2)] -> shared_dep lands at 3
    assert remapped.ns_index == 3
    assert remapped.id_type == nid.id_type
    assert remapped.id == nid.id
    assert to_model.namespace_array[3] == "urn:test:shared_dep"


def test_remap_nodeid_reuses_existing_index_on_repeat(ctx, ua_namespace):
    #? Unsure if this test should be kept as it doesn't make sense that the result should ever change
    from_model = register_model(ctx, "urn:test:from_model")
    to_model = register_model(ctx, "urn:test:to_model")
    dep_idx_in_from = ctx._get_ns_idx_relative_to_target(from_model, "urn:test:shared_dep")
    nid = NodeId.from_string(f"ns={dep_idx_in_from};i=7")

    first = ctx.remap_nodeid(nid, from_model, to_model)
    second = ctx.remap_nodeid(nid, from_model, to_model)

    assert first.ns_index == second.ns_index


# ---- _mint_global_idx ----

def test_mint_global_idx_assigns_sequential_indices_across_models(ctx, ua_namespace):
    model_a = register_model(ctx, "urn:test:model_a")
    node_a = make_node("ns=0;i=1", "0:A", ua_namespace)
    node_b = make_node("ns=1;i=1", "1:B", model_a)

    ctx._mint_global_idx(node_a)
    ctx._mint_global_idx(node_b)

    assert node_a._global_idx == 0
    assert node_b._global_idx == 1
    assert ctx.nodes_by_global_idx == [node_a, node_b]
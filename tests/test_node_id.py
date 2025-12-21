import pytest

from ua_nemo.node_model import NodeId, NodeIdType

#TODO Vibe coded tests, review these

# --- NodeIdType enum behaviour ---------------------------------------------


def test_nodeidtype_values():
    assert NodeIdType.NUMERIC.value == "i"
    assert NodeIdType.STRING.value == "s"
    assert NodeIdType.GUID.value == "g"
    assert NodeIdType.OPAQUE.value == "b"


def test_nodeidtype_from_char():
    assert NodeIdType("i") is NodeIdType.NUMERIC
    assert NodeIdType("s") is NodeIdType.STRING
    assert NodeIdType("g") is NodeIdType.GUID
    assert NodeIdType("b") is NodeIdType.OPAQUE


# --- from_string parsing ---------------------------------------------------


@pytest.mark.parametrize(
    "text, ns_index, id_type, identifier",
    [
        ("i=42", 0, NodeIdType.NUMERIC, 42),
        ("ns=2;i=1234", 2, NodeIdType.NUMERIC, 1234),
        ("s=Hello", 0, NodeIdType.STRING, "Hello"),
        ("ns=3;s=MyVar", 3, NodeIdType.STRING, "MyVar"),
        ("g=550e8400-e29b-41d4-a716-446655440000", 0, NodeIdType.GUID,
         "550e8400-e29b-41d4-a716-446655440000"),
        ("ns=4;g=550e8400-e29b-41d4-a716-446655440000", 4, NodeIdType.GUID,
         "550e8400-e29b-41d4-a716-446655440000"),
        ("b=YWJjZGU=", 0, NodeIdType.OPAQUE, "YWJjZGU="),
        ("ns=5;b=YWJjZGU=", 5, NodeIdType.OPAQUE, "YWJjZGU="),
    ],
)
def test_from_string_parses_correctly(text, ns_index, id_type, identifier):
    nid = NodeId.from_string(text)

    assert nid.ns_index == ns_index
    assert nid.id_type is id_type
    assert nid.id == identifier


def test_from_string_trims_whitespace():
    nid = NodeId.from_string("   ns=2;i=1234   ")
    assert nid.ns_index == 2
    assert nid.id_type is NodeIdType.NUMERIC
    assert nid.id == 1234


def test_from_string_numeric_is_int():
    n1 = NodeId.from_string("i=42")
    n2 = NodeId.from_string("ns=2;i=1234")
    assert isinstance(n1.id, int)
    assert isinstance(n2.id, int)


@pytest.mark.parametrize(
    "text",
    [
        "",                # empty
        "ns=",             # missing id part
        "ns=1;",           # missing id part
        "ns=x;i=42",       # invalid ns index
        "ns=1;z=42",       # unknown id type
        "ns=1;i=",         # missing identifier
        "i=",              # missing identifier
        "ns=1;invalid",    # no '=' in id part
    ],
)
def test_from_string_rejects_invalid(text):
    with pytest.raises(ValueError):
        NodeId.from_string(text)


# --- to_string / __str__ behaviour ----------------------------------------


@pytest.mark.parametrize(
    "text, canonical",
    [
        ("i=42", "i=42"),                        # ns 0 → omit ns=0;
        ("ns=0;i=42", "i=42"),                   # equivalent textual form
        ("ns=2;i=1234", "ns=2;i=1234"),
        ("s=Hello", "s=Hello"),
        ("ns=3;s=MyVar", "ns=3;s=MyVar"),
        ("g=550e8400-e29b-41d4-a716-446655440000",
         "g=550e8400-e29b-41d4-a716-446655440000"),
        ("ns=4;g=550e8400-e29b-41d4-a716-446655440000",
         "ns=4;g=550e8400-e29b-41d4-a716-446655440000"),
        ("b=YWJjZGU=", "b=YWJjZGU="),
        ("ns=5;b=YWJjZGU=", "ns=5;b=YWJjZGU="),
    ],
)
def test_to_string_canonical(text, canonical):
    nid = NodeId.from_string(text)
    assert nid.to_string() == canonical


def test_str_always_includes_ns_prefix():
    n0 = NodeId.from_string("i=42")
    n2 = NodeId.from_string("ns=2;i=1234")

    assert str(n0) == "ns=0;i=42"
    assert str(n2) == "ns=2;i=1234"


# --- equality & hashing ----------------------------------------------------


def test_equality_same_values():
    a = NodeId.from_string("ns=2;i=1234")
    b = NodeId.from_string("ns=2;i=1234")
    assert a == b
    assert not (a != b)


def test_inequality_different_ns_or_id_or_type():
    a = NodeId.from_string("ns=1;i=1")
    b = NodeId.from_string("ns=2;i=1")
    c = NodeId.from_string("s=1")
    d = NodeId.from_string("i=2")

    assert a != b
    assert a != c
    assert a != d


def test_equality_with_non_nodeid_returns_not_implemented():
    nid = NodeId.from_string("i=1")
    assert (nid == 1) is NotImplemented or (nid == 1) is False  # depending on Python's resolution


def test_hash_consistent_with_equality():
    a = NodeId.from_string("ns=2;i=1234")
    b = NodeId.from_string("ns=2;i=1234")
    c = NodeId.from_string("ns=2;i=1235")

    s = {a}
    assert b in s
    assert c not in s

    d = {a: "value"}
    assert d[b] == "value"
    assert c not in d


# --- __repr__ behaviour ----------------------------------------------------


def test_repr_contains_useful_info():
    nid = NodeId.from_string("ns=2;i=1234")
    rep = repr(nid)

    # Loose checks to avoid over-coupling on formatting
    assert rep.startswith("NodeId(")
    assert "ns=2" in rep
    assert "NUMERIC" in rep
    assert "1234" in rep


def test_repr_exact_format():
    nid = NodeId.from_string("ns=2;i=1234")
    assert repr(nid) == "NodeId(ns=2, type=NUMERIC, identifier=1234)"

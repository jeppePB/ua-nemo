import pytest

from ua_nemo.types import QualifiedName


def test_from_string_with_namespace_prefix():
    assert QualifiedName.from_string("2:Foo") == QualifiedName(2, "Foo")

def test_from_string_uses_default_ns_without_prefix():
    assert QualifiedName.from_string("Foo", default_ns=1) == QualifiedName(1, "Foo")

def test_from_string_keeps_colon_in_name_when_prefix_is_not_a_number():
    assert QualifiedName.from_string("a:b") == QualifiedName(0, "a:b")

def test_to_string_round_trips():
    assert QualifiedName.from_string(QualifiedName(3, "Bar").to_string()) == QualifiedName(3, "Bar")

@pytest.mark.parametrize("ns_index", [0, 65535])
def test_ns_index_boundaries_are_accepted(ns_index):
    assert QualifiedName(ns_index, "Foo").ns_index == ns_index

@pytest.mark.parametrize("ns_index", [-1, 65536])
def test_ns_index_out_of_range_raises(ns_index):
    with pytest.raises(ValueError):
        QualifiedName(ns_index, "Foo")

def test_ns_index_must_be_int():
    with pytest.raises(ValueError):
        QualifiedName("1", "Foo")  # type: ignore[arg-type]

def test_name_must_be_str():
    with pytest.raises(TypeError):
        QualifiedName(1, None)  # type: ignore[arg-type]

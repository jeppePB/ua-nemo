import pytest
from ua_nemo.node_model import Namespace, NamespaceContext

TEST_URI = "http://yourcompany.com/test-types/"

def test_create_namespace():
    ns = Namespace()

    assert isinstance(ns.namespace_context, NamespaceContext)
    assert ns.name is None
    assert ns.uri is None

def test_set_uri():
    ns = Namespace()
    

    ns.uri = TEST_URI

    assert ns.uri == TEST_URI
    assert ns.name == "test-types"
    assert TEST_URI in ns.namespace_context.namespace_dict_uri

def test_set_uri_error():
    ns = Namespace()
    ns.uri = TEST_URI
    with pytest.raises(ValueError):
        ns.uri = TEST_URI
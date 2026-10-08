import pytest
from ua_nemo.core import Namespace, Reference

@pytest.fixture(autouse=True)
def reset_default_namespace_context():
    Namespace._default_ctx = None
    yield
    Namespace._default_ctx = None

@pytest.fixture
def ns():
    namespace = Namespace()
    namespace.uri = "urn:example"
    return namespace

@pytest.fixture
def make_ref():
    def _make(reference_type, target_nodeid, is_forward=True, source=None):
        return Reference(reference_type, target_nodeid, is_forward, source)
    return _make
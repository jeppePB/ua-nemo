import pytest

import ua_nemo.node_model as nm
from ua_nemo.node_model import Namespace

# ---------- FAKES / TEST DOUBLES ----------

class FakeNamespace:
    """
    Minimal Namespace double:
    - .uri
    - .resolve(ref_type)
    - .find_by_nodeid(nodeid)
    plus a small helper for tests.
    """

    def __init__(self, uri="urn:example"):
        self.uri = uri
        self._nodes = {}          # nodeid -> Node
        self._resolve_map = {}    # ref_type -> nodeid (string or NodeId)
        self.nid_to_idx = {}      # make sure nothing breaks when attempting to get idx of a node
        self.is_ua_namespace = False
        
    def register(self, nodeid, node):
        """Helper for tests: make find_by_nodeid return this node."""
        self._nodes[nodeid] = node
        
    def register_alias(self, alias, nodeid):
        self._resolve_map[alias] = nodeid

    def find_by_nodeid(self, nodeid):
        return self._nodes.get(nodeid)

    def resolve(self, reference_type):
        """
        Mimics Namespace.resolve: map a reference type to a NodeId (or string).
        If not configured, return the input unchanged.
        """
        return self._resolve_map.get(reference_type, reference_type)


class FakeReference:
    """
    Minimal Reference double sufficient for Node logic.
    """

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

    def __repr__(self):
        return f"FakeReference({self.reference_type!r}, {self.target_nodeid!r}, {self.is_forward})"


# ---------- FIXTURES ----------

@pytest.fixture
def ns():
    """
    Create a fresh FakeNamespace for every test.
    """
    return FakeNamespace(uri="urn:example")


@pytest.fixture
def fake_ref():
    """
    Factory for FakeReference so tests read cleanly.
    Usage:
        ref = fake_ref("i=40", "ns=1;i=999", is_forward=True)
    """
    def _make(reference_type, target_nodeid, is_forward=True, source=None):
        return FakeReference(reference_type, target_nodeid, is_forward, source)
    return _make

@pytest.fixture(autouse=True)
def reset_default_namespace_context():
    Namespace._default_namespace_context = None
    yield
    Namespace._default_namespace_context = None

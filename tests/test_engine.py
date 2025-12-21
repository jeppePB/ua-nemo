import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from ua_nemo.engine import ModelBuilderEngine

class DummyNodeModel:
    def __init__(self):
        self.aliases = {'Alias1': 'Value1'}
        self.namespace_context = MagicMock()
    def find_by_browse_name(self, name):
        if name == 'KnownRef':
            DummyNode = MagicMock()
            DummyNode.node_id = 'NodeId123'
            return [DummyNode]
        raise Exception('Not found')
    def resolve(self, name):
        return 'AliasNodeId'

class DummyRow:
    def __init__(self, type_namespace, reference_type):
        self.type_namespace = type_namespace
        self.reference_type = reference_type

def test_load_typelibraries():
    engine = ModelBuilderEngine()
    dummy_loader = MagicMock()
    dummy_loader.load_from_path.return_value = {'UA': 'SomeModel'}
    with patch('ua_nemo.engine.TypeLibraryXMLLoader', return_value=dummy_loader):
        engine.load_typelibraries(Path('dummy.xml'))
    assert 'UA' in engine.typelibraries
    assert engine.typelibraries['UA'] == 'SomeModel'

def test_get_typelibrary_found():
    engine = ModelBuilderEngine()
    engine.typelibraries = {'UA': 'SomeModel'}
    assert engine.get_typelibrary('UA') == 'SomeModel'

def test_get_typelibrary_not_found():
    engine = ModelBuilderEngine()
    with pytest.raises(ValueError):
        engine.get_typelibrary('Missing')

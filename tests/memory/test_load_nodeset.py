import memray
import pytest

@pytest.mark.memory_profile
@pytest.mark.limit_memory("500 MB")
def test_isa95_load_memory(isa95_nodeset_path):
    from ua_nemo.parsers import NodesetLoader
    loader = NodesetLoader()
    loader.load_from_file_list([isa95_nodeset_path])

@pytest.mark.memory_profile
@pytest.mark.limit_memory("500 MB")
def test_isa95_load_memory(isa95_nodeset_path, enttype_nodeset_path):
    from ua_nemo.parsers import NodesetLoader
    loader = NodesetLoader()
    loader.load_from_file_list([isa95_nodeset_path, enttype_nodeset_path])
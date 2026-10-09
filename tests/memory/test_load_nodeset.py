import memray
import pytest

@pytest.mark.memory_profile
@pytest.mark.limit_memory("500 MB")
def test_isa95_load_memory(isa95_nodeset_path):
    from ua_nemo.loading import load_from_file_list
    load_from_file_list([isa95_nodeset_path])

@pytest.mark.memory_profile
@pytest.mark.limit_memory("500 MB")
def test_isa95_load_memory(isa95_nodeset_path, enttype_nodeset_path):
    from ua_nemo.loading import load_from_file_list
    load_from_file_list([isa95_nodeset_path, enttype_nodeset_path])
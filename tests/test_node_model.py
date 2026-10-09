from pathlib import Path
from ua_nemo.core import Namespace
from ua_nemo.loading import load_from_file_list

#TODO The namespace context is a class variable, needs to be reset between test runs. That is not being done currently.
UA_PATH = Path.cwd() / "typelibraries" / "ua_nodeset" / "Opc.Ua.NodeSet2.xml"
TEST_TYPELIBS = Path.cwd() / "tests" / "files" / "test-typelibs" / "test-types.xml"

def test_default_namespace_context():
    """
    The namespace_context should be the exact same object across all node models,
    but the namespace_array should be individual.
    """

    model_one = Namespace()
    model_one.uri = "http://model_one.org"
    model_two = Namespace()
    model_two.uri = "http://model_two.org"

    assert model_one.ns_ctx is model_two.ns_ctx
    assert model_one.namespace_array != model_two.namespace_array
    
def test_namespace_array():
    ctx = load_from_file_list([])
    ua_model = ctx.get_namespace_by_name("UA")

    model_one = Namespace(ctx)
    model_one.uri = "http://model_one.org"
    
    assert len(model_one.namespace_array) == 2
    assert model_one.namespace_array[0] == ua_model.uri
    assert model_one.namespace_array[1] == model_one.uri

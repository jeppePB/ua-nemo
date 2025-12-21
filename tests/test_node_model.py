from pathlib import Path
from ua_nemo.node_model import Node, Namespace, NodeClass
from ua_nemo.xml_loader import TypeLibraryXMLLoader

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

    assert model_one.namespace_context is model_two.namespace_context
    assert model_one.namespace_array != model_two.namespace_array
    
def test_namespace_array():
    ua_model:Namespace = TypeLibraryXMLLoader().load_from_file_list([])["UA"]

    model_one = Namespace()
    model_one.uri = "http://model_one.org"
    
    assert len(model_one.namespace_array) == 2
    assert model_one.namespace_array[0] == ua_model.uri
    assert model_one.namespace_array[1] == model_one.uri

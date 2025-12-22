from ua_nemo.node_definitions import NodeClass
from ua_nemo.node_model import Namespace, Node
from ua_nemo.engine import ModelBuilderEngine
from tests.test_minimal_example import TYPELIB_PATH

def test_classify_hierarchical_references():
    engine = ModelBuilderEngine()
    engine.load_typelibraries()
    ua_model = engine.get_typelibrary("UA")

    hierarchical_references_node = ua_model.find_by_nodeid("i=33")
    organizes_node = ua_model.find_by_browse_name("Organizes")[0]
    
    # Modelling rule is not hierarchical
    modelling_rule_node = ua_model.find_by_browse_name("HasModellingRule")[0]
    
    assert hierarchical_references_node.base_type == hierarchical_references_node.node_id
    assert organizes_node.base_type == organizes_node.node_id
    assert modelling_rule_node.base_type is None
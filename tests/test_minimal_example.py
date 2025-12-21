from pathlib import Path

import pandas as pd

from ua_nemo.engine import ModelBuilderEngine
from ua_nemo.node_model import NodeId, Namespace, TypeNode
from ua_nemo.type_instantiator import TypeInstantiator
from ua_nemo.utils import load_nodes, load_objects, load_relations, normalize_bool
from ua_nemo.xml_builder import dump_model_to_xml_streaming
from ua_nemo.xml_loader import TypeLibraryXMLLoader


TEST_FP = Path.cwd() / "tests" / "files"
TYPELIB_PATH = TEST_FP / 'test-typelibs'
OBJECTS_PATH = TEST_FP / "objects"
REFERENCES_PATH = TEST_FP / "references"
XML_OUT = Path.cwd() / "tests" / "output"

XML_OUT.mkdir(exist_ok=True)


TEST_URI = "http://www.MyDevelopmentNodeset.com/DEVELOPMENT/"


engine : ModelBuilderEngine = None


def create_nodes(model:Namespace, objects:pd.DataFrame, relations:pd.DataFrame):
    global engine

    rels_by_source = relations.groupby("source_node")

    # Create node instances
    for row in objects.itertuples(index=False):
        row_dict = row._asdict()

        #* Extract required args
        node_id = row_dict.pop("nodeid")
        browse_name = row_dict.pop("browsename")
        typename = row_dict.pop("nodetype")
        type_namespace = row_dict.pop("type_namespace")

        instantiated_node = engine.instantiate_node(
            typelib_name=type_namespace,
            target_model=model,
            typename=typename,
            node_id=node_id,
            browse_name=browse_name,
            **row_dict
        )

        #* Extract relations where the current nodeid == sourceid and create them

        node_rels = rels_by_source.get_group(node_id)
        for row in node_rels.itertuples(index=False):
            ref_type = engine.get_ref_from_browsename(row, model)
            target_node = row.target_node
            try:    
                NodeId.from_string(row.target_node)
            except:
                #! Fix this. Very hacky.
                #* Wtf am I even doing here.. End result is that the target node id has the namespace remapped to fit with the namespace
                #* array of the model that is being built at least
                parts = target_node.split(".")
                typelib = engine.get_typelibrary(parts[0])
                target = typelib.find_by_browse_name(parts[1])[0]
                context = model.namespace_context
                target_node = context.remap_nodeid(target.node_id, typelib, model)
            instantiated_node.add_reference(reference_type=ref_type.to_string(), target_nodeid=target_node, is_forward=normalize_bool(row.IsForward))


def test_minimal_example():
    global engine
    engine = ModelBuilderEngine()
    engine.load_typelibraries(TYPELIB_PATH)
    model = Namespace()
    model.uri = TEST_URI

    objects = load_objects(OBJECTS_PATH)
    relations = load_relations(REFERENCES_PATH)

    create_nodes(model, objects, relations)
    dump_model_to_xml_streaming(model, file_path=XML_OUT / "minimal_test.xml")

    # schema_validator.validate_nodeset_xsd(XML_OUT / "minimal_test.xml", "UANodeSet.xsd")

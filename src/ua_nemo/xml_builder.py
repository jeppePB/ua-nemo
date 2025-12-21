from pathlib import Path
import xml.etree.ElementTree as ET
from xml.dom import minidom
from .node_model import Namespace, Node
from .node_definitions import NODE_CLASSES
from .utils import bool_to_str

def dump_model_to_xml(model:Namespace, file_path=None):
    #TODO Rewrite to use LXML. This also barely supports literally anything.
    NS_UA = "http://opcfoundation.org/UA/2011/03/UANodeSet.xsd"
    nsmap = {"ua": NS_UA}
    ET.register_namespace('', NS_UA)

    root = ET.Element("UANodeSet", xmlns=NS_UA)

    # NamespaceUris
    ns_uris = ET.SubElement(root, "NamespaceUris")
    for uri in model.namespace_array:
        if uri == "http://opcfoundation.org/UA/":
            continue
        uri_elem = ET.SubElement(ns_uris, "Uri")
        uri_elem.text = uri

    # Aliases
    aliases = ET.SubElement(root, "Aliases")
    for alias in model.aliases:
        alias_elem = ET.SubElement(aliases, "Alias")
        alias_elem.attrib["Alias"] = alias
        alias_elem.text = model.aliases[alias].to_string()

    #TODO add models

    # Nodes
    for node in model.nodes_by_id.values():
        #TODO Make this more memory efficient. Maybe don't create the full model in memory before dumping?
        tag = NODE_CLASSES[node.node_class]
        elem = ET.SubElement(root, tag)

        # Core attributes (NodeId, BrowseName, etc.)
        elem.attrib["NodeId"] = node.node_id.to_string()
        elem.attrib["BrowseName"] = node.attributes.get("BrowseName", node.browse_name)

        for attr_key, attr_val in node.attributes.items():
            if attr_key not in ("NodeId", "BrowseName"):
                if type(attr_val, bool):
                    attr_val = bool_to_str(attr_val)
                elem.attrib[attr_key] = str(attr_val)

        # Subnodes (DisplayName, Description, etc.)
        for sub_key, sub_val in node.subnodes.items():
            child = ET.SubElement(elem, sub_key)
            child.text = str(sub_val)

        # References
        if node.references:
            refs_elem = ET.SubElement(elem, "References")
            for ref in node.references:
                ref_elem = ET.SubElement(refs_elem, "Reference")
                ref_elem.attrib["ReferenceType"] = ref.reference_type
                if not ref.is_forward:
                    ref_elem.attrib["IsForward"] = "false"
                ref_elem.text = ref.target_nodeid.to_string()

    # Write output
    xml_str = ET.tostring(root, encoding="utf-8")
    pretty = minidom.parseString(xml_str).toprettyxml(indent="  ")

    if file_path:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(pretty)
    return pretty

from lxml import etree as ET

def dump_model_to_xml_streaming(model:Namespace, file_path:Path):
    NS_UA = "http://opcfoundation.org/UA/2011/03/UANodeSet.xsd"
    nsmap = {None: NS_UA}

    print("Writing to XML")

    with ET.xmlfile(file_path, encoding="utf-8") as xf:
        xf.write_declaration()

        with xf.element("UANodeSet", nsmap=nsmap):

            # NamespaceUris
            with xf.element("NamespaceUris"):
                for ext_model in model.namespace_array:
                    if ext_model != "http://opcfoundation.org/UA/":
                        with xf.element("Uri"):
                            xf.write(ext_model)
                        xf.write("\n")
                xf.write("\n")

            # Aliases
            with xf.element("Aliases"):
                for alias, nodeid in model.aliases.items():
                    with xf.element("Alias", Alias=alias):
                        xf.write(nodeid.to_string())
                    xf.write("\n")
                xf.write("\n")

            # Nodes
            for node in model.nodes_by_id.values():
                tag = NODE_CLASSES[node.node_class]
                node_attrs = {
                    "NodeId": node.node_id.to_string(),
                    "BrowseName": node.attributes.get("BrowseName", node.browse_name),
                }
                for key, val in node.attributes.items():
                    if key not in ("NodeId", "BrowseName"):
                        if isinstance(val, bool) or str(val).lower() in ["true", "false"]:
                            val = str(val).lower()
                        node_attrs[key] = str(val)

                with xf.element(tag, node_attrs):
                    for sub_key, sub_val in node.subnodes.items():
                        with xf.element(sub_key):
                            xf.write(str(sub_val))
                        xf.write("\n")

                    if node.references:
                        with xf.element("References"):
                            for ref in node.references:
                                ref_attrs = {"ReferenceType": ref.reference_type}
                                if not ref.is_forward:
                                    ref_attrs["IsForward"] = "false"
                                with xf.element("Reference", ref_attrs):
                                    xf.write(ref.target_nodeid.to_string())
                                xf.write("\n")
                        xf.write("\n")
                xf.write("\n")
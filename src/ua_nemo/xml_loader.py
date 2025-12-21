from pathlib import Path

import xml.etree.ElementTree as ET
from .node_model import Node, Namespace, NodeId

from .node_definitions import NodeClass, resolve_node_class
from .utils import split_node_fields

UA_NODESET = Path(__file__).resolve().parent / "typelibraries" / "ua_nodeset"

HIERARCHICAL_UA_REFS = ["i=33"]
NON_HIERARCHICAL_USA_REFS = ["i=32"]
HAS_SUBTYPE = "i=45"
class TypeLibraryXMLLoader:

    refs_to_classify:list[Node]

    def load(self, xml_path:Path) -> tuple[bool, dict|Path]:
        model = Namespace()
        self.refs_to_classify = []

        ns = {'ua': 'http://opcfoundation.org/UA/2011/03/UANodeSet.xsd'}
        context = ET.iterparse(xml_path, events=("start", "end"))
        event, root = next(context)
        models_elem = root.find("ua:Models", ns)
        if models_elem is not None:
            model_elem = models_elem.findall("ua:Model", ns)
            if len(model_elem) == 0:
                pass
            else: 
                model_elem = model_elem[0]
                model.uri = model_elem.attrib["ModelUri"]
                model.ns_info.update(model_elem.attrib)
                model.ns_info['required_models'] = []

                required_models = model_elem.findall("ua:RequiredModel", ns)
                for required_model in required_models:
                    model.ns_info['required_models'].append(required_model.attrib)
                    if not required_model.attrib.get("ModelUri") in model.namespace_context.namespace_dict_uri:
                        # Required model has not been loaded yet, defer to later time
                        del model
                        return False, xml_path
                
        aliases_elem = root.find("ua:Aliases", ns)
        log_interval = 10000
        counter = 0
        if aliases_elem is not None:
            for alias_elem in aliases_elem.findall("ua:Alias", ns):
                model.add_alias(
                    alias_name = alias_elem.attrib.get("Alias"),
                    nodeid_text = alias_elem.text)
        
        for event, elem in context:
            if counter % log_interval == 0:
                print(f"\rProcessing xml elements:\t {counter}", end="", flush=True)
            counter += 1
            if event == "end":
                tag = self.get_clean_tag(elem.tag)
                if not model.uri:
                    if tag == "Model":
                        model.uri = elem.attrib["ModelUri"]
                    elif tag == "Uri": # If model name is not properly defined, extract from first available uri
                        model.uri = elem.text
                if tag == "Uri":
                    model.add_namespace(elem.text)
                elif tag in ("UAObjectType", "UAVariableType", "UAReferenceType", "UADataType", "UAObject", "UAVariable"):
                    if tag == "UAReferenceType":
                        node = self.parse_xml_node(elem, model, ns)
                        self.refs_to_classify.append(node)
                    else:
                        node = self.parse_xml_node(elem, model, ns)
                    model.add_node(node)
                    elem.clear()

        self.classify_references()
        print("\r\033[K", end='', flush=True)  # Clear the line
        print(f"Finished processing {counter} xml elements")
        typelib_dict = {model.name: model}

        return True, typelib_dict
    
    def _resolve_ua_basetype(self, node:Node) -> tuple[NodeId]:
        namespace = node.namespace
        if node.base_type:
            # Function has been recursively called, and the parent node has a base type
            return node.base_type
        
        if node.node_id.to_string() in HIERARCHICAL_UA_REFS:
            # Node is base hierarchical type
            return node.node_id
        
        for ref in node.references:
            ref_type = namespace.resolve(ref.reference_type)
            if ref_type.to_string() == HAS_SUBTYPE and not ref.is_forward:
                if ref.target_nodeid.to_string() in HIERARCHICAL_UA_REFS:
                    # Parent type is the base hierarchical type, return nodeid of current type as it's a 'hierarchical category'.
                    return node.node_id
                else:
                    # No matches, search for base type of parent type node
                    parent_node = namespace.find_by_nodeid(ref.target_nodeid)
                    return self._resolve_ua_basetype(parent_node)

    def classify_references(self):
        for node in self.refs_to_classify:
            base_type = self._resolve_ua_basetype(node)
            
            node.base_type = base_type
            self.refs_to_classify.remove(node)

    def load_from_path(self, typelib_path: Path) -> dict[str, Namespace]:
        """Loads typelibraries from a directory path

        Args:
            typelib_path (Path): Path to directory containing typelibrary files

        Returns:
            dict: Mapping of model_name:model
        """
        xml_files = list(typelib_path.glob("*.xml"))
        return self.load_from_file_list(xml_files)
        
    def load_from_file_list(self, file_list:list[str|Path], deferred=0) -> dict[str, Namespace]:
        """Legacy support

        Args:
            file_list (list[str | Path]): List of files

        Returns:
            dict: Mapping of model_name:model
        """
        # Max attempts to load typelibraries if required models are missing
        max_attempts = 3

        file_list = [Path(f) for f in file_list]
        
        load_order:list[Path] = []
        
        if deferred == 0:
            if not any("Opc.Ua.NodeSet2" in file.name for file in file_list):
                load_order.append(Path(UA_NODESET / "Opc.Ua.NodeSet2.xml"))
            else:
                for file in file_list:
                    if "Opc.Ua.NodeSet2" in file.name:
                        load_order.append(file)
                        break
        
        load_order += sorted(file_list, key=lambda p: p.name)

        typelibraries = {}
        
        deferred_load = []

        
        for file in load_order:
            if file.is_file():
                load_status, result = self.load(file)
                if load_status:
                    typelibraries.update(result)
                else:
                    print(f"Performing deferred load of {result} later..")
                    deferred_load.append(result)
        
        if len(deferred_load) > 0:
            if deferred >= max_attempts:
                raise Exception(f"Failed to load all typelibraries. Missing requirements for files:\n{deferred_load}")
            typelibraries.update(self.load_from_file_list(deferred_load, deferred+1))
        
        return typelibraries
    
    @staticmethod
    def get_clean_tag(tag:str)->str:
        """Cleans up the xml tag 

        Args:
            tag (str): Raw tag

        Returns:
            str: Cleaned tag
        """
        return tag.split("}", 1)[-1] if "}" in tag else tag
    
    def parse_reference(self, ref_elem):
        #TODO Implement by extracting from parse_xml_node
        ref_type = ref_elem.attrib["ReferenceType"]
        is_forward = ref_elem.attrib.get("IsForward", "true").lower() != "false" # Convert to bool
        target_id = ref_elem.text

    def parse_xml_node(self, elem, model:Namespace, ns):
        tag = self.get_clean_tag(elem.tag)

        node_id = elem.attrib.pop("NodeId")
        browse_name = elem.attrib.pop("BrowseName")
        node_class = resolve_node_class(tag)
        references = []
        raw = dict(elem.attrib)

        for child in elem:
            subtag = self.get_clean_tag(child.tag)
            if subtag not in ("References",):
                text = "".join(child.itertext()).strip()
                raw[subtag] = text

        attributes, subnodes = split_node_fields(node_class, raw)

        # Extract references
        for refs_elem in elem.findall("ua:References", ns):
            for ref_elem in refs_elem.findall("ua:Reference", ns):
                ref_type = ref_elem.attrib["ReferenceType"]
                is_forward = ref_elem.attrib.get("IsForward", "true").lower() != "false"
                target_id = model.resolve(ref_elem.text)
                references.append(
                    {
                        "reference_type": ref_type,
                        "target_nodeid": target_id,
                        "is_forward": is_forward
                     })

        node = Node(node_id, browse_name, node_class, model, attributes, subnodes)
        for ref in references:
            node.add_reference(**ref)

        if node.node_class == NodeClass.ReferenceType:
            self.refs_to_classify.append(node)

        return node


if __name__ == "__main__":
    loader = TypeLibraryXMLLoader()
    
    
    print("Success")
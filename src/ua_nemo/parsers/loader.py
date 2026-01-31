from pathlib import Path
from typing import Callable, Iterator
import logging

import xml.etree.ElementTree as ET

from ua_nemo.node_model import Node, Namespace, NodeId

from ua_nemo.node_definitions import NodeClass
from .dtos import ParsedReference, ParsedNode

logger = logging.getLogger(__name__)

UA_NODESET = Path(__file__).resolve().parent.parent / "typelibraries" / "ua_nodeset"

HIERARCHICAL_UA_REFS = ["i=33"]
NON_HIERARCHICAL_USA_REFS = ["i=32"]
HAS_SUBTYPE = "i=45"

# Missing views and methods
SUPPORTED_NODE_TAGS = {
    "UAObjectType", "UAVariableType", "UAReferenceType",
    "UADataType", "UAObject", "UAVariable",
}

def clean_tag(tag:str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag

def extract_raw_fields(elem) -> dict:
    raw = dict(elem.attrib)
    for child in elem:
        subtag = clean_tag(child.tag)
        if subtag == "References":
            continue
        raw[subtag] = "".join(child.itertext()).strip()
    return raw

def extract_references(elem, ns) -> tuple[ParsedReference, ...]:
    out: list[ParsedReference] = []
    for refs_elem in elem.findall("ua:References", ns):
        for ref_elem in refs_elem.findall("ua:Reference", ns):
            ref_type = ref_elem.attrib["ReferenceType"]
            target_text = (ref_elem.text or "").strip()
            is_forward = ref_elem.attrib.get("IsForward", "true").lower() != "false"
            out.append(ParsedReference(ref_type, target_text, is_forward))
    return tuple(out)

def iter_parsed_nodes(xml_path: Path, ns:set) -> Iterator[ParsedNode]:
    context = ET.iterparse(xml_path, events=("start", "end"))
    event, root = next(context)

    for event, elem in context:
        if event != "end":
            continue

        tag = clean_tag(elem.tag)
        if tag not in SUPPORTED_NODE_TAGS:
            continue

        node_id_text = elem.attrib.get("NodeId")
        browse_name = elem.attrib.get("BrowseName")

        raw = extract_raw_fields(elem)
        # ensure NodeId/BrowseName aren't duplicated inside raw
        raw.pop("NodeId", None)
        raw.pop("BrowseName", None)

        refs = extract_references(elem, ns)

        yield ParsedNode(
            tag=tag,
            node_id_text=node_id_text,
            browse_name=browse_name,
            raw=raw,
            references=refs,
        )

        elem.clear()

def parse_namespace_models(root, model: "Namespace", ns:set) -> bool:
    models_elem = root.find("ua:Models", ns)
    if models_elem is not None:
        model_elems = models_elem.findall("ua:Model", ns)
        if model_elems:
            model_elem = model_elems[0]
            model.uri = model_elem.attrib.get("ModelUri", model.uri)
            model.ns_info.update(model_elem.attrib)
            model.ns_info["required_models"] = []
            for req in model_elem.findall("ua:RequiredModel", ns):
                model.ns_info["required_models"].append(req.attrib)
                req_uri = req.attrib.get("ModelUri")
                if req_uri and req_uri not in model.namespace_context.namespace_dict_uri:
                    return False
    return True

def parse_aliases(root, model: "Namespace", ns:str):
    aliases_elem = root.find("ua:Aliases", ns)
    if aliases_elem is not None:
        for alias_elem in aliases_elem.findall("ua:Alias", ns):
            model.add_alias(alias_elem.attrib.get("Alias"), alias_elem.text)

def parse_uri(root, model: "Namespace", ns:str):
    for uri_elem in root.findall(".//ua:Uri", ns):
        if uri_elem.text:
            model.add_namespace(uri_elem.text.strip())

class NodesetLoader:
    def __init__(
        self,
        namespace_factory: Callable[[], "Namespace"] = None,
        node_factory: Callable[..., "Node"] = None,
        resolve_node_class: Callable[[str], "NodeClass"] = None,
        split_node_fields: Callable[["NodeClass", dict], tuple[dict, dict]] = None,
        progress: Callable[[int], None] | None = None
    ):
        
        # To make the class more easily testable, it is possible to swap out each component with a test method.
        if namespace_factory is None or node_factory is None or resolve_node_class is None or split_node_fields is None:
            from ua_nemo.node_model import Node, Namespace
            from ua_nemo.node_definitions import resolve_node_class as _rnc
            from ua_nemo.utils import split_node_fields as _snf
            namespace_factory = namespace_factory or Namespace
            node_factory = node_factory or Node
            resolve_node_class = resolve_node_class or _rnc
            split_node_fields = split_node_fields or _snf
        
        self._namespace_factory = namespace_factory
        self._node_factory = node_factory
        self._resolve_node_class = resolve_node_class
        self._split_node_fields = split_node_fields
        self._progress = progress

    def load(self, xml_path: Path, missing_requirements_strategy:str="defer") -> tuple[bool, dict | Path]:
        model = self._namespace_factory()
        ns = {"ua": "http://opcfoundation.org/UA/2011/03/UANodeSet.xsd"}

        context = ET.iterparse(xml_path, events=("start", "end"))
        event, root = next(context)

        ok = parse_namespace_models(root, model, ns)
        if not ok:
            if missing_requirements_strategy == "defer":
                del(model)
                return False, xml_path
            elif missing_requirements_strategy == "ignore":
                logger.warning("One or more required models are missing. Some functionality might be broken.")
                pass
        
        parse_aliases(root, model, ns)
        parse_uri(root, model, ns)

        refs_to_classify = []

        counter = 0
        
        for parsed in iter_parsed_nodes(xml_path, ns):
            counter += 1
            if self._progress and counter % 10000 == 0:
                self._progress(counter)
            
            if not model.uri:
                if parsed.tag == "Model" and "ModelUri" in parsed.raw:
                    model.uri = parsed.raw["ModelUri"]
                
            node_class = self._resolve_node_class(parsed.tag)
            attributes, subnodes = self._split_node_fields(node_class, dict(parsed.raw))

            node = self._node_factory(
                parsed.node_id_text,
                parsed.browse_name,
                node_class,
                model,
                attributes,
                subnodes
            )

            # Apply refs with alias resolution
            for r in parsed.references:
                node.add_reference(
                    reference_type=model.resolve(r.reference_type),
                    target_nodeid=model.resolve(r.target_nodeid_text),
                    is_forward=r.is_forward
                )
            model.add_node(node)

            # Classify reference type nodes (hierarchical/non-hierarchical) later
            if node_class == NodeClass.ReferenceType:
                refs_to_classify.append(node)
        
        self._classify_references(refs_to_classify)
    
        return (True, {model.name: model})
    
    def _classify_references(self, refs_to_classify: list["Node"]):
        for node in refs_to_classify:
            node.base_type = self._resolve_ua_basetype(node)

    def _resolve_ua_basetype(self, node: "Node") -> "NodeId":
        namespace = node.namespace

        if node.base_type:
            return node.base_type

        if node.node_id.to_string() in HIERARCHICAL_UA_REFS:
            return node.node_id

        for ref in node.references:
            ref_type = namespace.resolve(ref.reference_type)
            if ref_type.to_string() == HAS_SUBTYPE and not ref.is_forward:
                if ref.target_nodeid.to_string() in HIERARCHICAL_UA_REFS:
                    return node.node_id
                parent_node = namespace.find_by_nodeid(ref.target_nodeid)
                return self._resolve_ua_basetype(parent_node)

        return None

    def load_from_path(self, typelib_path: Path) -> dict[str, Namespace]:
        """Loads typelibraries from a directory path

        Args:
            typelib_path (Path): Path to directory containing typelibrary files

        Returns:
            dict: Mapping of model_name:model
        """
        xml_files = list(typelib_path.glob("*.xml"))
        return self.load_from_file_list(xml_files)
        
    def load_from_file_list(self, file_list:list[str|Path], handle_max_deferred_strategy:str="ignore", deferred=0) -> dict[str, Namespace]:
        """Legacy support

        Args:
            file_list (list[str | Path]): List of files

        Returns:
            dict: Mapping of model_name:model
        """
        # Max attempts to load namespaces if required models are missing
        max_attempts = 3
        max_deferred = deferred >= max_attempts

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

        namespace_dict = {}
        
        deferred_load = []

        
        for file in load_order:
            if file.is_file():
                if max_deferred:
                    load_status, result = self.load(file, handle_max_deferred_strategy)
                else:
                    load_status, result = self.load(file)
                if load_status:
                    namespace_dict.update(result)
                else:
                    print(f"Performing deferred load of {result} later..")
                    deferred_load.append(result)
        
        if len(deferred_load) > 0:
            if max_deferred:
                if handle_max_deferred_strategy == "raise":
                    raise Exception(f"Failed to load all typelibraries. Missing requirements for files:\n{deferred_load}")
            else:
                namespace_dict.update(self.load_from_file_list(deferred_load, deferred+1))
        
        return namespace_dict
    
        




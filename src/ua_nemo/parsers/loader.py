from pathlib import Path
from typing import Callable
import logging
from dataclasses import dataclass

import xml.etree.ElementTree as ET

from ua_nemo.core import Namespace
from ua_nemo.core import NodeId, Node
from ua_nemo.types import NamespaceMetadata
from ua_nemo.node_definitions import NodeClass
from ua_nemo.parsers.dtos import ParsedReference
from ua_nemo.core.exceptions import MissingRequiredModelError

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

@dataclass
class NodesetParseState:
    in_namespace_uris: bool = False
    header_checked: bool = False
    node_count: int = 0
    nodeset_end: bool = False

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
        
def parse_models_event(event: str, elem, ns_metadata: Namespace) -> None:
    if event != "end":
        return

    tag = clean_tag(elem.tag)

    if tag == "Model":
        ns_metadata.append(NamespaceMetadata.from_xml_attrib(elem.attrib, is_mandatory=False))

    elif tag == "RequiredModel":
        ns_metadata.append(NamespaceMetadata.from_xml_attrib(elem.attrib, is_mandatory=True))


def parse_alias_event(event: str, elem, model: Namespace) -> None:
    if event != "end":
        return
    if clean_tag(elem.tag) != "Alias":
        return
    model.add_alias(elem.attrib.get("Alias"), elem.text)

def parse_namespace_uri_event(event: str, elem, ns_array: list, state: NodesetParseState) -> None:
    tag = clean_tag(elem.tag)

    # This control block is there just in case there is ever
    # an uri that is outside namespaceuris.
    if event == "start" and tag == "NamespaceUris":
        state.in_namespace_uris = True
        return

    if event == "end" and tag == "NamespaceUris":
        state.in_namespace_uris = False
        elem.clear()
        return

    if event == "end" and tag == "Uri" and state.in_namespace_uris:
        if elem.text:
            ns_array.append(elem.text)

def try_parse_node_event(
    event: str,
    elem,
    model: Namespace,
    ns,
    *,
    resolve_node_class,
    split_node_fields,
    node_factory,
) -> "Node | None":
    if event != "end":
        return None

    tag = clean_tag(elem.tag)
    if tag not in SUPPORTED_NODE_TAGS:
        return None

    node_id_text = elem.attrib.get("NodeId")
    browse_name = elem.attrib.get("BrowseName")

    raw = extract_raw_fields(elem)
    raw.pop("NodeId", None)
    raw.pop("BrowseName", None)

    refs = extract_references(elem, ns)

    node_class = resolve_node_class(tag)
    attributes, subnodes = split_node_fields(node_class, dict(raw))

    node = node_factory(
        node_id_text,
        browse_name,
        node_class,
        model,
        attributes,
        subnodes
    )

    # Apply refs with alias resolution (Namespace.resolve returns NodeId)
    for r in refs:
        node.add_reference(
            reference_type=model.resolve(r.reference_type),
            target_nodeid=model.resolve(r.target_nodeid_text),
            is_forward=r.is_forward,
        )

    elem.clear()
    return node

def check_nodeset_end(event:str, elem) -> bool:
    return event == "end" and elem.tag.endswith("UANodeSet")

class NodesetLoader:
    def __init__(
        self,
        namespace_factory: Callable[[], Namespace] = None,
        node_factory: Callable[..., Node] = None,
        resolve_node_class: Callable[[str], NodeClass] = None,
        split_node_fields: Callable[[NodeClass, dict], tuple[dict, dict]] = None,
        progress: Callable[[int], None] | None = None
    ):
        
        # To make the class more easily testable, it is possible to swap out each component with a test method.
        if namespace_factory is None or node_factory is None or resolve_node_class is None or split_node_fields is None:
            from ua_nemo.core import Namespace, Node
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

    def load(self, xml_path: Path, missing_requirements_strategy: str = "defer") -> dict[str, Namespace]:
        model = self._namespace_factory()
        ns = {"ua": "http://opcfoundation.org/UA/2011/03/UANodeSet.xsd"}

        state = NodesetParseState()
        refs_to_classify = []

        context = ET.iterparse(xml_path, events=("start", "end"))
        _, root = next(context)
        
        ns_metadata: list[NamespaceMetadata] = []
        ns_array: list[str] = []

        for event, elem in context:
            if not state.header_checked:
                parse_models_event(event, elem, ns_metadata)
                parse_alias_event(event, elem, model)
                parse_namespace_uri_event(event, elem, ns_array, state)
                state.nodeset_end = check_nodeset_end(event, elem)

            node = try_parse_node_event(
                event,
                elem,
                model,
                ns,
                resolve_node_class=self._resolve_node_class,
                split_node_fields=self._split_node_fields,
                node_factory=self._node_factory
            )

            if node is None and not state.nodeset_end:
                continue

            # First time a supported node is hit, header has been fully parsed. Set namespace data, check deps and fail fast.
            if not state.header_checked:
                self._process_header_data(model, ns_metadata, ns_array)
                self._check_missing_requirements(model, xml_path, missing_requirements_strategy)
                state.header_checked = True
                if state.nodeset_end:
                    logger.debug("Found no nodes in namespace")
                    break

            state.node_count += 1
            if self._progress and state.node_count % 10000 == 0:
                self._progress(state.node_count)

            model.add_node(node)

            if node.node_class == NodeClass.ReferenceType:
                refs_to_classify.append(node)
            
        if not state.header_checked:
            self._check_missing_requirements(model, xml_path, missing_requirements_strategy)
        
        self._classify_references(refs_to_classify)
        return {model.name: model}
    
    def _process_header_data(self, model: Namespace, ns_metadata: list[NamespaceMetadata], ns_array: list[str]):
        """Because some namespaces don't use the model tag, the namespace uri sometimes have to be pulled from the ns_array"""
        for metadata in ns_metadata:
            if not metadata.is_mandatory and not model.uri:
                model.uri = metadata.uri
                model.metadata = metadata
            elif metadata.is_mandatory:
                model.dependencies.append(metadata)
        
        for uri in ns_array:
            if not model.uri and not uri.endswith("/UA/"):
                model.uri = uri
                continue
            model.add_namespace(uri)

    def _check_missing_requirements(self, model: Namespace, xml_path: Path, strategy: str):
        missing = [
            dep for dep in model.dependencies
            if dep.is_mandatory and dep.uri not in model.namespace_context.namespace_dict_uri
        ]

        if missing:
            if strategy == "defer" or strategy == "raise":
                raise MissingRequiredModelError(
                    requesting=model.metadata,  
                    missing=missing,
                    nodeset_path=xml_path
                )
            elif strategy == "ignore":
                logger.warning(
                    "Missing required model(s) for %s while loading %s: %s",
                    model.uri, xml_path, ", ".join(m.uri for m in missing)
                )
            else:
                raise ValueError(f"Unsupported strategy: {strategy}")

    
    def _classify_references(self, refs_to_classify: list[Node]):
        for node in refs_to_classify:
            node.base_type = self._resolve_ua_basetype(node)

    def _resolve_ua_basetype(self, node: "Node") -> "NodeId":
        namespace = node.namespace

        if node.base_type:
            return node.base_type

        if node.node_id.to_string() in HIERARCHICAL_UA_REFS:
            return node.node_id

        for ref in node.references:
            if ref.reference_type.to_string() == HAS_SUBTYPE and not ref.is_forward:
                if ref.target_nodeid.to_string() in HIERARCHICAL_UA_REFS:
                    return node.node_id
                parent_node = namespace.find_by_nodeid(ref.target_nodeid)
                if parent_node is None:
                    continue  # Parent node namespace has not been loaded
                return self._resolve_ua_basetype(parent_node)

        return None

    def load_from_path(self, typelib_path: Path, handle_max_deferred_strategy:str="ignore") -> dict[str, Namespace]:
        """Loads typelibraries from a directory path

        Args:
            typelib_path (Path): Path to directory containing typelibrary files

        Returns:
            dict: Mapping of model_name:model
        """
        xml_files = list(typelib_path.glob("*.xml"))
        return self.load_from_file_list(xml_files, handle_max_deferred_strategy)
        
    def load_from_file_list(self, file_list:list[str|Path], handle_max_deferred_strategy:str="ignore", deferred=0) -> dict[str, Namespace]:
        """Legacy support

        Args:
            file_list (list[str | Path]): List of files

        Returns:
            dict: Mapping of model_name:model
        """
        # Max attempts to load namespaces if required models are missing
        max_attempts = 3
        max_attempts_reached = deferred >= max_attempts

        file_list = [Path(f) for f in file_list]
        
        load_order:list[Path] = []
        
        if deferred == 0:
            if not any("Opc.Ua.NodeSet2" in file.name for file in file_list):
                load_order.append(Path(UA_NODESET / "Opc.Ua.NodeSet2.xml"))
            else:
                load_order.append(next(f for f in file_list if "Opc.Ua.NodeSet2" in f.name))
        
        load_order += sorted(file_list, key=lambda p: p.name)

        namespace_dict: dict[str, Namespace]= {}
        deferred_load: list[Path] = []

        for file in load_order:
            if not file.is_file():
                continue
            try:
                strategy = handle_max_deferred_strategy if max_attempts_reached else "defer"
                namespace_dict.update(self.load(file, missing_requirements_strategy=strategy))
            except MissingRequiredModelError as e:
                if max_attempts_reached and handle_max_deferred_strategy == "raise":
                    logger.error("Failed to load required models for nodeset")
                    raise e
                else:
                    logger.info("Deferring load of %s: %s", file, e)
                    deferred_load.append(file)
            
        if deferred_load:
            namespace_dict.update(self.load_from_file_list(deferred_load, handle_max_deferred_strategy, deferred + 1))

        return namespace_dict
    
        




from __future__ import annotations
from enum import Enum

from . import node_definitions
from .node_definitions import NodeClass
from .protocols import AbstractContext

class NodeIdType(Enum):
    NUMERIC = "i"
    STRING = "s"
    GUID = "g"
    OPAQUE = "b"


class NodeId:
    __slots__ = ("ns_index", "id_type", "id")

    ns_index:int
    id_type:NodeIdType
    id: int|str

    def __init__(self, ns_index:int, id_type: NodeIdType, id:int|str):
        self.ns_index = ns_index
        self.id_type = id_type
        self.id = id

    def __repr__(self) -> str:
        cls_name = self.__class__.__name__
        return (f"{cls_name}("
                f"ns={self.ns_index}, "
                f"type={self.id_type.name}, "
                f"identifier={self.id!r})")
    
    def __str__(self) -> str:
        return f"ns={self.ns_index};{self.id_type.value}={self.id}"
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, NodeId):
            return NotImplemented
        return (
            self.ns_index == other.ns_index
            and self.id_type == other.id_type
            and self.id == other.id
        )

    def __hash__(self):
        return hash((self.ns_index, self.id_type, self.id))
   
    @classmethod
    def from_string(cls, raw:str) -> "NodeId":
        raw = raw.strip()

        # Default NS-idx is 0 according to OPC UA spec
        ns_index = 0
        id_part = None

        # Split namespace if present
        if raw.startswith("ns="):
            ns_part, id_part = raw.split(";", 1)
            ns_index = int(ns_part.split("=", 1)[1]) 
        else:
            id_part = raw

        try:
            id_char, ident_str = id_part.split("=", 1)
        except ValueError:
            raise ValueError(f"Invalid Nodeid string: {raw!r}")
        
        # Map id type char to enum
        try:
            id_type = NodeIdType(id_char)
        except ValueError:
            raise ValueError(f"Unknown NodeId type '{id_char}' in {raw!r}")
        
        # Convert identifier
        if id_type is NodeIdType.NUMERIC:
            identifier = int(ident_str)
        else:
            identifier = ident_str
        
        return cls(ns_index, id_type, identifier)
    
    def to_string(self) -> str:
        if self.ns_index == 0:
            return f"{self.id_type.value}={self.id}"
        else:
            return f"ns={self.ns_index};{self.id_type.value}={self.id}"
        
class Reference:
    __slots__ = ("reference_type", "target_nodeid", "is_forward", "source")
    reference_type: str
    source_id: NodeId
    target_nodeid: NodeId
    is_forward: bool

    def __repr__(self) -> str:
        cls = self.__class__.__name__
        return (f"{cls}("
                f"type={self.reference_type!r}, "
                f"target={self.target_nodeid}, "
                f"is_forward={self.is_forward})")

    def __str__(self) -> str:
        direction = "->" if self.is_forward else "<-"
        return f"{self.reference_type} {direction} {self.target_nodeid}"

    def __init__(self, reference_type: str, target_nodeid: str|NodeId, is_forward:bool, source:Node):
        self.reference_type = reference_type
        if not isinstance(target_nodeid, NodeId):
            target_nodeid = NodeId.from_string(target_nodeid)
        self.target_nodeid = target_nodeid
        self.is_forward = is_forward
        self.source = source

    @property
    def is_hierarchical(self) -> bool:
        # Only hierarchical refs have base type for now
        ref_node = self.get_base_type_node()
        return ref_node.base_type is not None

    @property
    def base_type(self) -> str:
        ref_node = self.get_base_type_node()
        return ref_node.display_name

    @property
    def target(self) -> Node:
        return self.source.namespace.find_by_nodeid(self.target_nodeid)

    def get_base_type_node(self) -> Node:
        ref_nid = self.source.namespace.resolve(self.reference_type)
        return self.source.namespace.find_by_nodeid(ref_nid)


class Node:
    __slots__ = ("node_id", "browse_name", "node_class", "references", "attributes", "subnodes", "namespace", "base_type")

    namespace: Namespace
    node_id: NodeId
    browse_name: str
    node_class: NodeClass
    references:list[Reference]
    attributes:dict
    subnodes:dict
    base_type:NodeId

    display_name: str
    description: str
    type_definition: NodeId | None

    is_abstract : bool
    is_object : bool
    is_variable : bool

    node_uri : str
    type_uri : str
    
    def __init__(
            self, 
            node_id: str|NodeId, 
            browse_name:str, 
            node_class: NodeClass, 
            namespace:Namespace,
            attributes:dict={}, 
            subnodes:dict={},
            ):
        
        if not isinstance(node_id, NodeId):
            node_id = NodeId.from_string(node_id)
        
        self.node_id = node_id
        self.browse_name = browse_name
        self.node_class = node_class
        self.references = []
        self.attributes = attributes  # xml attributes
        self.subnodes = subnodes # subnodes like displayname, value etc.
        self.namespace = namespace
        self.base_type = None

        if not "DisplayName" in subnodes:
            subnodes["DisplayName"] = browse_name
    
    def __repr__(self) -> str:
        cls_name = self.__class__.__name__
        node_class = getattr(self.node_class, "name", self.node_class)
        return (f"{cls_name}(node_id={self.node_id!r}, "
                f"browse_name={self.browse_name!r}, "
                f"node_class={node_class!r})")
    
    @property
    def is_abstract(self) -> bool:
        return self.node_class in node_definitions.TYPE_CLASSES
    
    @property
    def is_object(self) -> bool:
        return self.node_class == NodeClass.Object
    
    @property
    def is_variable(self) -> bool:
        return self.node_class == NodeClass.Variable
    
    @property
    def display_name(self) -> str:
        return self.subnodes.get("DisplayName", "")
    
    @property
    def description(self) -> str:
        return self.subnodes.get("Description", "")
    
    @property
    def node_uri(self) -> str:
        namespace_uri = self.namespace.uri
        nid_id = self.node_id.id.replace("=","_")
        return f"{namespace_uri}#{nid_id}"

    @property
    def type_uri(self) -> str:
        type_node = self.namespace.find_by_nodeid(self.type_definition)
        if not type_node and self.is_abstract:
            type_node = self
        type_namespace = type_node.namespace.uri
        type_browsename = type_node.browse_name.split(":", 1)[-1]
        return f"{type_namespace}#{type_browsename}"
    
    @property
    def type_definition(self) -> NodeId:
        for ref in self.references:
            if ref.reference_type == "i=40":
                return ref.target_nodeid
        return None
    
    @property
    def hierarchical_parents(self) -> list[Reference]:
        return self.get_hierarchical_references(is_forward=False)
        
    
    @property
    def hierarchical_children(self) -> list[Reference]:
        return self.get_hierarchical_references(is_forward=True)

    @property
    def value(self):
        return self.subnodes.get("Value")
    
    def get_hierarchical_references(self, is_forward:bool) -> list[Reference]:
        hierarchical_refs = []
        for ref in self.references:
            if not ref.is_forward == is_forward:
                continue
            ref_type = self.namespace.resolve(ref.reference_type)
            ref_type_node = self.namespace.find_by_nodeid(ref_type)
            if ref_type_node.base_type:
                hierarchical_refs.append(ref)
        return hierarchical_refs
                
    def add_reference(self, reference_type: str, target_nodeid: str, is_forward:bool=True):
        ref = Reference(reference_type, target_nodeid, is_forward, self)
        if ref not in self.references:
            self.references.append(Reference(reference_type, target_nodeid, is_forward, self))
        
class Namespace:
    #TODO Add ".from_nodeset" function to load nodemodels from files
    
    _uri: str

    namespace_array: list
    namespace_context: AbstractContext = None
    aliases: dict[str, NodeId]
    is_type_namespace: bool
    name: str
    nodes_by_id: dict[str, Node]

    ns_info: dict

    def __init__(self, namespace_context:AbstractContext = None):
        self.name = None
        self._uri = None
        self.is_type_namespace = False
        self.nodes_by_id = {}
        self.nodes_by_browse_name = {}
        self.namespace_array = []
        self.ns_info = {}
        
        self.namespace_context = namespace_context
        
        self.aliases = {}

    def __repr__(self) -> str:
        cls = self.__class__.__name__
        return (f"{cls}("
                f"name={self.name!r}, "
                f"uri={self._uri!r}, "
                f"namespaces={len(self.namespace_array)}, "
                f"nodes={len(self.nodes_by_id)})")

    def __str__(self) -> str:
        ns_info = ", ".join(self.namespace_array) if self.namespace_array else "[]"
        return (f"NodeModel '{self.name}' "
                f"(URI={self._uri}, namespaces={ns_info}, nodes={len(self.nodes_by_id)})")

    @property
    def uri(self):
        return self._uri
    
    @uri.setter
    def uri(self, uri:str):
        if self.uri:
            raise ValueError("Attempting to set URI of model that already has an URI set.")
        if uri is None:
            return
        if not self.name:
            split_uri = uri.strip("/").split("/")
            is_url = False
            for substr in split_uri:
                if ".com" in substr or ".org" in substr:
                    is_url = True
                    break
            if is_url:
                com_idx = 0
                for idx, substr in enumerate(split_uri):
                    if ".com" in substr or ".org" in substr:
                        com_idx = idx
                self.name = "_".join(split_uri[com_idx+1:])
            else:
                self.name = uri.strip("/").split("/")[-1]
        
        self._uri = uri
        #TODO Remove separate handling of namespaces in model and global ns context
        self.namespace_context.register_model(self)
    
    def resolve(self, nodeid_or_alias: str) -> NodeId:
        # Fast path: a real NodeId string?
        if isinstance(nodeid_or_alias, NodeId):
            return nodeid_or_alias
        
        # Alias?
        if self.aliases.get(nodeid_or_alias):
            return self.aliases[nodeid_or_alias]
        
        try:
            return NodeId.from_string(nodeid_or_alias)
        except KeyError:
            raise ValueError(f"Unknown alias or bad NodeId: {nodeid_or_alias}")
        
    def add_namespace(self, ns_uri: str):
        if ns_uri in self.namespace_array:
            return
        self.namespace_array.append(ns_uri)

    def get_namespace_by_index(self, ns_idx: int) -> str:
        return self.namespace_array[ns_idx]

    def add_node(self, node: Node):   
        self.nodes_by_id[node.node_id.to_string()] = node
        self.nodes_by_browse_name.setdefault(node.browse_name, []).append(node)
        
        if not self.is_type_namespace:
            if node.node_class in node_definitions.TYPE_CLASSES:
                self.is_type_namespace = True

    def add_alias(self, alias_name: str, nodeid_text: str):
        # nodeid_text can be "i=63", "ns=0;i=63", "ns=1;s=Thing", etc.
        if ";" in nodeid_text:  # expanded form
            nid = NodeId.from_string(nodeid_text)
        else:
            # Short form like "i=63", "s=MyId", etc. -> default to ns=0
            nid = NodeId.from_string(f"ns=0;{nodeid_text}")
        self.aliases[alias_name] = nid

    def _get_model_for_ns_index(self, ns_idx: int):
        ns_uri = self.get_namespace_by_index(ns_idx)
        return self.namespace_context.get_model_by_uri(ns_uri)

    def find_by_nodeid(self, node_id: str | NodeId) -> Node|ReferenceNode:
        # Normalize
        nid = node_id if isinstance(node_id, NodeId) else NodeId.from_string(node_id)
        ns = nid.ns_index

        # local
        if ns == 1:
            return self.nodes_by_id.get(nid.to_string())

        # UA namespace
        if ns == 0:
            if self.name == "UA":
                return self.nodes_by_id.get(nid.to_string())
            else:
                target_model = self._get_model_for_ns_index(ns)
                return target_model.nodes_by_id.get(nid.to_string())

        # Any other namespace: delegate
        target_model = self._get_model_for_ns_index(ns)
        
        # Normalize the nid to 1 as the node will be local to the target model
        normalized_nid = NodeId(
            ns_index=1,
            id_type = nid.id_type,
            id = nid.id
        )

        normalized_nid.ns_index = 1
        return target_model.nodes_by_id.get(normalized_nid.to_string())

        
    def find_by_browse_name(self, browse_name: str) -> list[Node]:
        #TODO Clean this up
        if not browse_name.startswith("1") and not self.name == "UA":
            browse_name = f"1:{browse_name}"
        return self.nodes_by_browse_name.get(browse_name, [])

class ReferenceNode(Node):
    __slots__ = ("base_type",)

    def __init__(self, base_type, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_type = base_type


class TypeNode():
    
    browsename: str
    
    def __init__(self, type_namespace:str, browsename:str):
        pass
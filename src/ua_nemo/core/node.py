from ua_nemo.core import NodeId, Reference
from ua_nemo.types import QualifiedName
from ua_nemo.types._protocols import NamespaceLike

import ua_nemo.node_definitions as nd

#TODO Fix this bandaid
HIERARCHICAL_REF = NodeId.from_string("i=40")

class Node:
    __slots__ = (
        "minted_idx",
        "node_id", 
        "browse_name", 
        "node_class", 
        "references", 
        "attributes", 
        "subnodes", 
        "namespace", 
        "base_type",
    ) 

    minted_idx: int
    namespace: NamespaceLike
    node_id: NodeId
    browse_name: QualifiedName
    node_class: nd.NodeClass
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
            browse_name: str|QualifiedName, 
            node_class: nd.NodeClass, 
            namespace: NamespaceLike,
            attributes: dict=None, 
            subnodes: dict=None,
            ):
        
        self.minted_idx = None
        if not isinstance(node_id, NodeId):
            node_id = NodeId.from_string(node_id)
        
        self.attributes = {} if attributes is None else attributes # XML attributes
        self.subnodes = {} if subnodes is None else subnodes # Displayname, value etc.

        self.node_id = node_id
        if isinstance(browse_name, QualifiedName):
            self.browse_name = browse_name
        else:
            if namespace and namespace.is_ua_namespace:
                self.browse_name = QualifiedName.from_string(browse_name)
            else:
                self.browse_name = QualifiedName.from_string(browse_name, default_ns=1)

        self.node_class = node_class
        self.references = []
        self.namespace = namespace
        self.base_type = None

        if not "DisplayName" in self.subnodes:
            self.subnodes["DisplayName"] = self.browse_name.name
    
    def __repr__(self) -> str:
        cls_name = self.__class__.__name__
        node_class = getattr(self.node_class, "name", self.node_class)
        return (f"{cls_name}(node_id={self.node_id!r}, "
                f"browse_name={self.browse_name!r}, "
                f"node_class={node_class!r})")
    
    @property
    def browse_name_text(self) -> str:
        return self.browse_name.to_string()
    
    @property
    def is_abstract(self) -> bool:
        return self.node_class in nd.TYPE_CLASSES
    
    @property
    def is_object(self) -> bool:
        return self.node_class == nd.NodeClass.Object
    
    @property
    def is_variable(self) -> bool:
        return self.node_class == nd.NodeClass.Variable
    
    @property
    def display_name(self) -> str:
        return self.subnodes.get("DisplayName", "")
    
    @property
    def description(self) -> str:
        return self.subnodes.get("Description", "")
    
    @property
    def node_uri(self) -> str:
        namespace_uri = self.namespace.uri
        nid_id = f"{self.node_id.id_type.value}_{self.node_id.id}"
        return f"{namespace_uri}#{nid_id}"

    @property
    def type_uri(self) -> str:
        type_node = self.namespace.find_by_nodeid(self.type_definition)
        if not type_node and self.is_abstract:
            type_node = self
        type_namespace = type_node.namespace.uri
        type_browsename = type_node.browse_name.name
        return f"{type_namespace}#{type_browsename}"
    
    @property
    def type_definition(self) -> NodeId:
        for ref in self.references:
            if ref.reference_type == HIERARCHICAL_REF:
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
        """Returns a list of hierarchical references in a given direction.
        is_forward=False for parents
        is_forward=True for children
        """
        
        hierarchical_refs = []
        for ref in self.references:
            if not ref.is_forward == is_forward:
                continue
            ref_type = self.namespace.resolve(ref.reference_type)
            ref_type_node = self.namespace.find_by_nodeid(ref_type)
            #TODO Base type is currently only set for hierarchical refs. Need to clean this up.
            if ref_type_node.base_type:
                hierarchical_refs.append(ref)
        return hierarchical_refs
    
    def get_child(self, child_browse_name: str|QualifiedName, handle_multiple:str="fail") -> "Node":
        """handle_multiple: strategy used when model has not been properly build and multiple
        children have the same qualified name. 
        Options:
            - fail: raises AmbiguousChildError
            - ignore: returns a list of matching nodes"""
        if isinstance(child_browse_name, str):
            child_browse_name = QualifiedName.from_string(child_browse_name)
        return self.namespace.child_by_qname(self, child_browse_name, handle_multiple)
    
    def add_reference(self, reference_type: str, target_nodeid: str, is_forward:bool=True):
        ref = Reference(reference_type, target_nodeid, is_forward, self)
        if self.namespace:
            target_idx = self.namespace.nid_to_idx.get(target_nodeid)
            ref.target_idx = target_idx
        if ref not in self.references:
            self.references.append(ref)
        
from .node_model import Namespace, NodeClass, Node

from .utils import split_node_fields

class TypeInstantiator:
    #TODO This needs to be cleaned up a bit. Not sure I even like using a class for this.
    #TODO Rewrite
    def __init__(self, typelib_model:Namespace, target_model:Namespace):
        self.typelib_model = typelib_model
        self.target_model = target_model
        self.ns_context = target_model.namespace_context

    def instantiate(self, typename: str, instance_nodeid: str, instance_browsename: str, include_optional: bool = False, **kwargs) -> str:
        # Find typedefinition
        type_nodes = self.typelib_model.find_by_browse_name(typename)
        if not type_nodes:
            raise ValueError(f"Type {typename} not found in typelibrary")
        type_node = type_nodes[0]
        
        remapped_typedef = self.ns_context.remap_nodeid(type_node.node_id, self.typelib_model, self.target_model)
        raw_attrs = type_node.attributes | kwargs.get("rest", {})
        if "ParentNodeId" in raw_attrs:
            del(raw_attrs["ParentNodeId"])
        attrs, subnodes = split_node_fields(type_node.node_class, raw_attrs)
        # Instantiate node
        instance_node = Node(
            node_id=instance_nodeid,
            browse_name=instance_browsename,
            node_class=self._resolve_nodeclass_from_typenode(type_node),
            namespace=self.target_model,
            attributes=attrs,
            subnodes=subnodes
        )
        instance_node.add_reference("HasTypeDefinition", remapped_typedef.to_string())
        self.target_model.add_node(instance_node)

        # Instantiate children
        for ref in type_node.references:
            if ref.reference_type in ("HasComponent", "HasProperty", "HasOrderedComponent"):
                child_type_node = self.typelib_model.find_by_nodeid(ref.target_nodeid)
                if child_type_node and (self._is_mandatory(child_type_node) or include_optional):
                    child_instance_id = f"{instance_nodeid}.{child_type_node.browse_name.split(':', 1)[-1]}"
                    child_instance_browse = child_type_node.browse_name.split(":")[-1]
                    
                    # Recursive instantiation of child
                    self.instantiate(
                        typename=child_instance_browse,
                        instance_nodeid=child_instance_id,
                        instance_browsename=child_instance_browse,
                        include_optional=include_optional
                    )

                    # Add the reference from parent to child
                    instance_node.add_reference(ref.reference_type, child_instance_id)

        return instance_node.node_id

    def _is_mandatory(self, node:Node) -> bool:
        for ref in node.references:
            if ref.reference_type == "HasModellingRule" and ref.target_nodeid.to_string() in ("i=78", "ns=0;i=78"):
                return True
        return False

    def _resolve_nodeclass_from_typenode(self, type_node:Node) -> NodeClass:
        if type_node.node_class == NodeClass.ObjectType:
            return NodeClass.Object
        elif type_node.node_class == NodeClass.VariableType:
            return NodeClass.Variable
        # Typenode is an instance (for example a property of an instantiated typenode), so just return its type
        elif type_node.node_class in NodeClass:
            return type_node.node_class
        else:
            raise ValueError(f"Cannot instantiate from unsupported type class {type_node.node_class}")
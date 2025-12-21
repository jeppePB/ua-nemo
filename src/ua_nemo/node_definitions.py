"""Contains helper functions to be able to define which attributes are expected based on node type and which values should be created as subnodes, as well as finding node classes.
"""
from enum import IntEnum

COMMON_ATTRIBUTES = {"NodeId", "BrowseName"}

NODECLASS_SPECIAL_ATTRIBUTES = {
    "UAObject": {"EventNotifier"},
    "UAObjectType": {"IsAbstract"},
    "UAVariable": {"DataType", "ValueRank", "ArrayDimensions", "AccessLevel", "UserAccessLevel", "Historizing"},
    "UAVariableType": {"DataType", "ValueRank", "ArrayDimensions", "IsAbstract"},
    "UAReferenceType": {"IsAbstract", "Symmetric", "InverseName"},
    "UAMethod": {"Executable", "UserExecutable"},
    "UADataType": {"IsAbstract"},
    "UAView": {"ContainsNoLoops", "EventNotifier"},
}

def get_expected_attributes(node_tag: str):
    """Returns common attributes that all nodes can have, along with attributes specific to the nodeclass

    Args:
        node_tag (str): Tag to search for

    Returns:
        set: Set of tags that are expected for the nodeclass
    """
    return COMMON_ATTRIBUTES.union(NODECLASS_SPECIAL_ATTRIBUTES.get(node_tag, set()))

COMMON_SUBNODES = {"DisplayName", "Description", "References"}

NODECLASS_SPECIAL_SUBNODES = {
    "UAVariable": {"Value"},
    "UAVariableType": {"Value"},
    "UAReferenceType": {"InverseName"},
}

def get_expected_subnodes(node_tag: str):
    """Returns common subnodes that all nodes can have, along with subnodes specific to the subclass

    Args:
        node_tag (str): Tag to search for

    Returns:
        set: Set of subnodes that are expected for the subclass
    """
    return COMMON_SUBNODES.union(NODECLASS_SPECIAL_SUBNODES.get(node_tag, set()))

class NodeClass(IntEnum):
    Object = 1
    Variable = 2
    Method = 3
    ObjectType = 4
    VariableType = 5
    ReferenceType = 6
    DataType = 7
    View = 8

TYPE_CLASSES = [
    NodeClass.ObjectType,
    NodeClass.VariableType,
    NodeClass.ReferenceType,
    NodeClass.DataType
]

NODE_CLASSES = {
        NodeClass.Object: "UAObject",
        NodeClass.Variable: "UAVariable",
        NodeClass.Method: "UAMethod",
        NodeClass.ObjectType: "UAObjectType",
        NodeClass.VariableType: "UAVariableType",
        NodeClass.ReferenceType: "UAReferenceType",
        NodeClass.DataType: "UADataType",
        NodeClass.View: "UAView",
    }

STR_TO_NODE_CLASS = {v: k for k, v in NODE_CLASSES.items()}

def resolve_node_class(nodeclass:str|NodeClass) -> NodeClass|str:
    if isinstance(nodeclass, str):
        return STR_TO_NODE_CLASS[nodeclass]
    else:
        return NODE_CLASSES[nodeclass]
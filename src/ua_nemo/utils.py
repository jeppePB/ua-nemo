from .node_definitions import NodeClass, get_expected_attributes, get_expected_subnodes

def normalize_bool(input_string:str) -> bool:
    #! Hacky fix
    if isinstance(input_string, bool):
        return input_string
    elif not input_string:
        return True
    bool_str = input_string.upper()
    if bool_str in ["TRUE, FALSE"]:
        return bool_str == "TRUE"
    raise ValueError("Invalid input", input_string)

def bool_to_str(input_bool:bool|str) -> str:
    if isinstance(input_bool, str):
        return input_bool.lower()
    if input_bool:
        return "true"
    else:
        return "false"
    
def split_node_fields(node_class: NodeClass, raw: dict) -> tuple[dict, dict]:
    tag = {
        NodeClass.Object: "UAObject",
        NodeClass.Variable: "UAVariable",
        NodeClass.Method: "UAMethod",
        NodeClass.ObjectType: "UAObjectType",
        NodeClass.VariableType: "UAVariableType",
        NodeClass.ReferenceType: "UAReferenceType",
        NodeClass.DataType: "UADataType",
        NodeClass.View: "UAView",
    }[node_class]

    expected_attrs = get_expected_attributes(tag)
    expected_subs = get_expected_subnodes(tag)

    attrs = {}
    subs = {}
    if raw is not None and len(raw) > 0:
        for k, v in raw.items():
            if k in expected_attrs:
                attrs[k] = v
            elif k in expected_subs:
                subs[k] = v
            else:
                attrs[k] = v  # fallback
    return attrs, subs
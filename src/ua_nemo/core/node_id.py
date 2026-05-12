from enum import Enum
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
        if id_type == NodeIdType.NUMERIC:
            id = int(id)
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
        
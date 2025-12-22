from pathlib import Path

from .node_model import NodeId, Namespace
from .type_instantiator import TypeInstantiator
from .xml_loader import TypeLibraryXMLLoader

class NamespaceContext:
    #TODO Needs a cleanup, fairly sure this contains duplicate functionality
    namespace_dict: dict[str, Namespace] = {}
    namespace_dict_uri: dict[str, Namespace] = {}
    known_models: list[Namespace] = []

    #? Would I like to automatically load the ua nodeset here? 
    def register_model(self, model:Namespace):
        self.namespace_dict[model.name] = model
        self.namespace_dict_uri[model.uri] = model
        self.known_models.append(model.uri)

        if not model.name == "UA":
            ua_namespace = self.namespace_dict.get("UA")
            if ua_namespace is None:
                #TODO Make a proper warning
                print(f"UA namespace has not been loaded. Model {model.name} has an empty namespace on index 0 of its namespace array.")
            else:
                model.namespace_array.append(ua_namespace.uri)
            
        model.namespace_array.append(model.uri)
    
    def get_model(self, name:str=None, uri:str=None) -> Namespace | None:
        #TODO Refactor this
        if name == uri:
            raise ValueError("One of name or uri is required")
        if name:
            return self.namespace_dict.get(name)
        return self.namespace_dict_uri.get(uri)
    
    def get_model_by_uri(self, model_uri:str) -> Namespace:
        return self.namespace_dict_uri[model_uri]
    
    def get_or_add_namespace(self, target_model:Namespace, uri:str) -> int:
        if uri not in target_model.namespace_array:
            target_model.namespace_array.append(uri)
        return target_model.namespace_array.index(uri)

    def remap_nodeid(self, nid: NodeId, from_model:Namespace, to_model:Namespace) -> NodeId:
        uri = from_model.namespace_array[nid.ns_index]
        new_index = self.get_or_add_namespace(to_model, uri)
        return NodeId(
            ns_index = new_index,
            id_type = nid.id_type,
            id=nid.id)
    
    def empty(self):
        return len(self.namespace_dict) == 0

class ModelBuilderEngine:
    
    typelibraries : dict[str, Namespace]
    __type_instantiators : dict
    namespace_context : NamespaceContext

    def __init__(self):
        self.typelibraries = {}
        self.__type_instantiators = {}
        self.namespace_context = NamespaceContext()

    def load_typelibraries(
            self, 
            dir_path:Path = None, 
            file_list:list[Path|str] = None) -> None:
        """Loads typelibraries from either a directory path or a list of files.
        If neither are provider will just load the standard opcua nodeset.

        Args:
            dir_path (Path, optional): Path to directory containing typelibrary files. Defaults to None.
            file_list (list[Path | str], optional): List of files to load. Defaults to None.
        """
        loader = TypeLibraryXMLLoader(self.namespace_context)
        if dir_path:
            self.typelibraries = loader.load_from_path(dir_path)
        elif file_list:
            self.typelibraries = loader.load_from_file_list(file_list)
        else:
            self.typelibraries = loader.load_from_file_list([])

    def get_typelibrary(self, typelib_name : str) -> Namespace:
        typelib_model = self.typelibraries.get(typelib_name)
        if typelib_model is None:
            raise ValueError(f"Could not find typelibrary with name {typelib_name}.")
        return typelib_model
    
    def set_aliases(self, target_model : Namespace):
        target_model.aliases = self.get_typelibrary("UA").aliases
        
    def get_ref_from_browsename(self, row : tuple, target_model: Namespace) -> NodeId:
        typelib_model = self.get_typelibrary(row.type_namespace)

        #TODO This is not clean. Needs fixing.
        try:
            ref_nodeid = typelib_model.find_by_browse_name(row.reference_type)[0].node_id
        except:
            #* Check if this is an alias
            ref_nodeid = typelib_model.resolve(row.reference_type)
        remapped_nodeid = target_model.namespace_context.remap_nodeid(ref_nodeid, typelib_model, target_model)
        return remapped_nodeid
    
    def get_type_instantiator(self, typelib_name : str, target_model : Namespace) -> TypeInstantiator:
        if self.__type_instantiators.get(typelib_name) is not None:
            return self.__type_instantiators[typelib_name]
        typelib_model = self.get_typelibrary(typelib_name)
        instantiator = TypeInstantiator(typelib_model, target_model)
        self.__type_instantiators[typelib_name] = instantiator
        return instantiator
    
    def instantiate_node(self, typelib_name : str, target_model : Namespace, typename: str, node_id: str, browse_name: str, **kwargs) -> str:
        instantiator = self.get_type_instantiator(typelib_name, target_model)
        instantiator.instantiate(typename, node_id, browse_name, **kwargs)
        return target_model.find_by_nodeid(node_id)
    
    def get_typelibrary_by_index(self, idx:int) -> Namespace:
        typelib_name = list(self.typelibraries)[idx]
        return self.typelibraries.get(typelib_name)
    
    def find_node(self, ns_uri:str, node_id:NodeId):
        #TODO What I am doing here is actually finding the node model and then searching for the node within it.
        #TODO That is why I have to make this hacky change to the ns index.
        #TODO Refactor, check if still needed
        node_model = self.get_typelibrary_by_index(node_id.ns_index)
        if node_id.ns_index != 0:
            node_id.ns_index = 1
        return node_model.find_by_nodeid(node_id)

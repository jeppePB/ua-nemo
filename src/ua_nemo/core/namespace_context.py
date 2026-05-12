from __future__ import annotations

from ua_nemo.core.node_id import NodeId
from ua_nemo.types._protocols import NamespaceLike


class NamespaceContext:
    #TODO Needs a cleanup, fairly sure this contains duplicate functionality
    namespace_dict: dict[str, NamespaceLike] = {}
    namespace_dict_uri: dict[str, NamespaceLike] = {}
    known_models: list[str] = []    #TODO Check whether this can be removed

    #? Would I like to automatically load the ua nodeset here?
    def register_model(self, model: NamespaceLike) -> None:
        self.namespace_dict[model.name] = model
        self.namespace_dict_uri[model.uri] = model
        self.known_models.append(model.uri)

        if not model.name == "UA":
            ua_namespace = self.namespace_dict.get("UA")
            if ua_namespace is None:
                #TODO Make a proper warning
                print(f"UA namespace has not been loaded. Model {model.name} has an empty namespace on index 0 of its namespace array.")
            else:
                model.add_namespace(ua_namespace.uri)

        model.add_namespace(model.uri)

    def get_model(self, name: str = None, uri: str = None) -> NamespaceLike | None:
        #TODO Refactor this
        if name == uri:
            raise ValueError("One of name or uri is required")
        if name:
            return self.namespace_dict.get(name)
        return self.namespace_dict_uri.get(uri)

    def get_model_by_uri(self, model_uri: str) -> NamespaceLike:
        return self.namespace_dict_uri[model_uri]

    def get_or_add_namespace(self, target_model: NamespaceLike, uri: str) -> int:
        if uri not in target_model.namespace_array:
            target_model.namespace_array.append(uri)
        return target_model.namespace_array.index(uri)

    def remap_nodeid(self, nid: NodeId, from_model: NamespaceLike, to_model: NamespaceLike) -> NodeId:
        uri = from_model.namespace_array[nid.ns_index]
        new_index = self.get_or_add_namespace(to_model, uri)
        return NodeId(
            ns_index=new_index,
            id_type=nid.id_type,
            id=nid.id)

    def empty(self) -> bool:
        return len(self.namespace_dict) == 0

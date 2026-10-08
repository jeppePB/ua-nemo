from ua_nemo.core import NamespaceContext

from pathlib import Path

def load_from_path(dir_path: Path, handle_max_deferred_strategy:str = "ignore") -> NamespaceContext:
    from ua_nemo.parsers import NodesetLoader
    res = NodesetLoader().load_from_path(dir_path, handle_max_deferred_strategy)
    return list(res.values())[0].ns_ctx

def load_from_file_list(file_list: list[str|Path], handle_max_deferred_strategy:str = "ignore") -> NamespaceContext:
    from ua_nemo.parsers import NodesetLoader
    res = NodesetLoader().load_from_file_list(file_list, handle_max_deferred_strategy)
    return list(res.values())[0].ns_ctx
# ua-nemo

Parses OPC UA NodeSet XML files into an in-memory model and resolves references between namespaces.

## Installation

```bash
pip install ua-nemo
```

Requires Python 3.10+.

## Core concepts

- **`Namespace`** — an in-memory representation of one loaded NodeSet. Holds all nodes, aliases, and the namespace array for that model.
- **`NamespaceContext`** — a shared registry across all `Namespace` instances. Tracks which models are loaded and resolves cross-namespace node lookups.
- **`Node`** — a single OPC UA node with a node ID, browse name, node class, attributes, subnodes, and references.
- **`NodesetLoader`** — parses NodeSet XML files and populates `Namespace` objects.

## Loading NodeSet XML files

`NodesetLoader` always loads the standard OPC UA base NodeSet (`Opc.Ua.NodeSet2.xml`) automatically before any other files.

### Load from a directory

```python
from ua_nemo.parsers import NodesetLoader

loader = NodesetLoader()
namespaces = loader.load_from_path("path/to/nodesets/")
# Returns {"UA": <Namespace>, "my-types": <Namespace>, ...}
```

### Load from an explicit file list

```python
from pathlib import Path
from ua_nemo.parsers import NodesetLoader

loader = NodesetLoader()
namespaces = loader.load_from_file_list([
    Path("nodesets/Opc.Ua.NodeSet2.xml"),
    Path("nodesets/MyCompany.NodeSet2.xml"),
])
```

### Load a single file

```python
from pathlib import Path
from ua_nemo.parsers import NodesetLoader

loader = NodesetLoader()
namespaces = loader.load(Path("nodesets/MyCompany.NodeSet2.xml"))
```

### Missing dependencies

If a NodeSet declares a required model that has not been loaded yet, the loader defers it and retries after all other files are processed. This handles most load-order issues automatically. You can control the fallback behaviour with the `missing_requirements_strategy` parameter:

- `"defer"` (default) — retry after other files are loaded
- `"ignore"` — log a warning and continue
- `"raise"` — raise `MissingRequiredModelError` immediately

## Accessing namespaces

`load_from_path` and `load_from_file_list` return a `dict[str, Namespace]` keyed by the model name derived from the namespace URI.

```python
namespaces = loader.load_from_path("nodesets/")

ua = namespaces["UA"]
my_model = namespaces["my-types"]

print(my_model.uri)             # "http://yourcompany.com/my-types/"
print(my_model.namespace_array) # ["http://opcfoundation.org/UA/", "http://yourcompany.com/my-types/"]
```

All `Namespace` instances created without an explicit `NamespaceContext` share a single default context, so cross-namespace lookups work automatically.

## Accessing nodes

### By node ID

```python
# String form
node = namespace.find_by_nodeid("ns=1;i=1001")

# NodeId object
from ua_nemo.core import NodeId
nid = NodeId.from_string("ns=1;i=1001")
node = namespace.find_by_nodeid(nid)
```

`find_by_nodeid` resolves cross-namespace references: if the requested `ns` index points to a different loaded model, the lookup is forwarded there automatically.

### By browse name

```python
# Returns a list (browse names are not guaranteed unique)
nodes = namespace.find_by_browse_name("MyObject")
node = nodes[0]

# With explicit namespace index prefix
nodes = namespace.find_by_browse_name("1:MyObject")
```

## Working with nodes

```python
node = namespace.find_by_nodeid("ns=1;i=1001")

print(node.node_id)       # NodeId(ns=1, type=NUMERIC, identifier=1001)
print(node.browse_name)   # QualifiedName
print(node.display_name)  # str
print(node.node_class)    # NodeClass.Object / .Variable / .ObjectType / ...
print(node.attributes)    # dict of XML attributes
print(node.references)    # list[Reference]
```

### Traversing references

```python
for ref in node.references:
    print(ref.reference_type)  # NodeId
    print(ref.target_nodeid)   # NodeId
    print(ref.is_forward)      # bool
    target = ref.target        # resolves to Node via the namespace
```

## Module structure

```
ua_nemo/
  core/
    node_id.py           # NodeId and NodeIdType
    node.py              # Node
    reference.py         # Reference
    namespace.py         # Namespace
    namespace_context.py # NamespaceContext
    exceptions.py        # MissingRequiredModelError
  parsers/
    loader.py            # NodesetLoader
  types/
    qualified_name.py    # QualifiedName, NamespaceMetadata
    _protocols.py        # NamespaceLike, NodeLike protocols
  engine.py              # ModelBuilderEngine
  xml_builder.py         # dump_model_to_xml_streaming
  node_definitions.py    # NodeClass enum and field definitions
  utils.py               # split_node_fields, normalize_bool
```
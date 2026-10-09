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
- **`NodesetLoader`** — parses a single NodeSet XML file into a `Namespace`.

## Loading NodeSet XML files

`load_from_path` and `load_from_file_list` always load the standard OPC UA base NodeSet (`Opc.Ua.NodeSet2.xml`) automatically before any other files, and return a `NamespaceContext` holding every loaded namespace.

### Load from a directory

```python
from ua_nemo import load_from_path

ctx = load_from_path("path/to/nodesets/")
```

### Load from an explicit file list

```python
from pathlib import Path
from ua_nemo import load_from_file_list

ctx = load_from_file_list([
    Path("nodesets/Opc.Ua.NodeSet2.xml"),
    Path("nodesets/MyCompany.NodeSet2.xml"),
])
```

### Load a single file

```python
from pathlib import Path
from ua_nemo.parsers import NodesetLoader

namespace = NodesetLoader().load(Path("nodesets/MyCompany.NodeSet2.xml"))
```

### Missing dependencies

If a NodeSet declares a required model that has not been loaded yet, `load_from_path` and `load_from_file_list` defer it and retry after all other files are processed. This handles most load-order issues automatically. The `handle_max_deferred_strategy` parameter controls what happens if a model is still missing after the final attempt:

- `"ignore"` (default) — log a warning and continue
- `"raise"` — raise `MissingRequiredModelError`

`NodesetLoader.load` takes `missing_requirements_strategy` (`"defer"`, `"ignore"` or `"raise"`) for a single file.

## Accessing namespaces

`load_from_path` and `load_from_file_list` return a `NamespaceContext`. Look namespaces up by the model name derived from the namespace URI, or by URI.

```python
ctx = load_from_path("nodesets/")

ua = ctx.get_namespace_by_name("UA")
my_model = ctx.get_namespace_by_name("my-types")
same_model = ctx.get_namespace_by_uri("http://yourcompany.com/my-types/")

print(my_model.uri)             # "http://yourcompany.com/my-types/"
print(my_model.namespace_array) # ["http://opcfoundation.org/UA/", "http://yourcompany.com/my-types/"]
```

A `Namespace` created without an explicit `NamespaceContext` uses a shared default context, so cross-namespace lookups still work.

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
  engine.py              # ModelBuilderEngine (deprecated)
  loading.py             # load_from_path, load_from_file_list
  xml_builder.py         # dump_model_to_xml_streaming
  node_definitions.py    # NodeClass enum and field definitions
  utils.py               # split_node_fields, normalize_bool
```
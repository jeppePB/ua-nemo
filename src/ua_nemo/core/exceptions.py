import logging

from pathlib import Path

from ua_nemo.types import NamespaceMetadata

logger = logging.getLogger(__name__)
class MissingRequiredModelError(Exception):
    requesting:     NamespaceMetadata
    missing:        list[NamespaceMetadata]
    nodeset_path:   Path

    def __init__(
            self,
            *,
            requesting:NamespaceMetadata,
            missing: list[NamespaceMetadata],
            nodeset_path: Path):
        
        if not missing:
            raise ValueError("Missing must be a non-empty sequence of NamespaceMetadata")
        
        self.requesting = requesting
        self.missing = tuple(missing)
        self.nodeset_path = nodeset_path

        missing_str = ", ".join(m.uri for m in self.missing)
        where = f" while loading '{nodeset_path}'" if nodeset_path is not None else ""
        super().__init__(f"Missing required model(s) for '{requesting.uri}'{where}: {missing_str}")

    @property
    def missing_uris(self) -> tuple[str, ...]:
        return tuple(m.uri for m in self.missing)

class AmbiguousChildError(LookupError):
    pass
    
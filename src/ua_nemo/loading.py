from __future__ import annotations

import logging
from collections.abc import Sequence
from pathlib import Path

from ua_nemo.core import Namespace, NamespaceContext
from ua_nemo.core.exceptions import MissingRequiredModelError
from ua_nemo.parsers.loader import UA_NODESET, NodesetLoader

logger = logging.getLogger(__name__)

# Passes made with "defer" before the final pass applies handle_max_deferred_strategy.
MAX_DEFER_ATTEMPTS = 3

def load_from_path(
        dir_path: Path | str,
        handle_max_deferred_strategy: str = "ignore",
        ctx: NamespaceContext | None = None) -> NamespaceContext:
    """Loads every .xml file in a directory into a NamespaceContext."""
    return load_from_file_list(list(Path(dir_path).glob("*.xml")), handle_max_deferred_strategy, ctx)

def load_from_file_list(
        file_list: Sequence[str | Path],
        handle_max_deferred_strategy: str = "ignore",
        ctx: NamespaceContext | None = None) -> NamespaceContext:
    """Loads nodesets into a NamespaceContext. The base UA nodeset is always loaded first.

    A nodeset whose required models are not loaded yet is deferred and retried after the others.
    On the final attempt handle_max_deferred_strategy decides what happens ("ignore" or "raise").
    """
    if ctx is None:
        ctx = NamespaceContext()
    loader = NodesetLoader(namespace_factory=lambda: Namespace(ctx))

    files = [Path(f) for f in file_list]
    ua_file = next((f for f in files if "Opc.Ua.NodeSet2" in f.name), UA_NODESET / "Opc.Ua.NodeSet2.xml")
    pending = [ua_file] + sorted((f for f in files if f != ua_file), key=lambda p: p.name)

    for attempt in range(MAX_DEFER_ATTEMPTS + 1):
        final_attempt = attempt == MAX_DEFER_ATTEMPTS
        strategy = handle_max_deferred_strategy if final_attempt else "defer"
        deferred: list[Path] = []

        for file in pending:
            if not file.is_file():
                continue
            try:
                loader.load(file, missing_requirements_strategy=strategy)
            except MissingRequiredModelError as e:
                if final_attempt and handle_max_deferred_strategy == "raise":
                    logger.error("Failed to load required models for nodeset")
                    raise
                logger.info("Deferring load of %s: %s", file, e)
                deferred.append(file)

        pending = deferred
        if not pending:
            break

    return ctx

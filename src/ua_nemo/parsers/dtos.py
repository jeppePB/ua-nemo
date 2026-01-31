from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Iterator, Optional
import xml.etree.ElementTree as ET


@dataclass(frozen=True)
class ParsedReference:
    reference_type: str
    target_nodeid_text: str
    is_forward: bool


@dataclass(frozen=True)
class ParsedNode:
    tag: str                  # e.g. "UAObjectType"
    node_id_text: str
    browse_name: str
    raw: dict                 # includes attributes + child text fields
    references: tuple[ParsedReference, ...]
from __future__ import annotations
import logging

from pathlib import Path
from typing import Callable

from ua_nemo.parsers import NodesetLoader
from ua_nemo.parsers.loader import HAS_SUBTYPE, HIERARCHICAL_UA_REFS

from tests.test_parsers.stubs import (
    NodeStub,
    NamespaceStub,
    split_node_fields_stub,
    resolve_node_class_stub
)

UA_NS = "http://opcfoundation.org/UA/2011/03/UANodeSet.xsd"



# Helpers
def write_xml(tmp_path: Path, filename: str, xml_text: str) -> Path:
    p = tmp_path / filename
    p.write_text(xml_text, encoding="utf-8")
    return p


def make_loader(
        loaded_model_uris: set[str] | None = None, 
        progress: Callable[[int], None] | None = None) -> NodesetLoader:
    return NodesetLoader(
        namespace_factory=lambda: NamespaceStub(loaded_model_uris=loaded_model_uris),
        node_factory=NodeStub,
        resolve_node_class=resolve_node_class_stub,
        split_node_fields=split_node_fields_stub,
        progress=progress,
    )

def test_load_defers_when_required_model_missing(tmp_path):
    loader = make_loader(loaded_model_uris=set())

    xml_path = write_xml(
        tmp_path,
        "missing_req.xml",
        f"""\
        <UANodeSet xmlns="{UA_NS}">
            <Models>
                <Model ModelUri="urn:test:model">
                <RequiredModel ModelUri="urn:missing:model"/>
                </Model>
            </Models>
        </UANodeSet>
        """,
    )

    ok, result = loader.load(xml_path, missing_requirements_strategy="defer")
    assert ok is False
    assert result == xml_path


def test_load_ignores_missing_required_models_when_configured(tmp_path, caplog):
    loader = make_loader(loaded_model_uris=set())

    xml_path = write_xml(
        tmp_path,
        "ignore_req.xml",
        f"""\
        <UANodeSet xmlns="{UA_NS}">
            <Models>
                <Model ModelUri="urn:test:model">
                    <RequiredModel ModelUri="urn:missing:model"/>
                </Model>
            </Models>
            <UAObjectType NodeId="i=1001" BrowseName="0:Foo">
                <DisplayName>Foo</DisplayName>
            </UAObjectType>
        </UANodeSet>
        """,
    )

    with caplog.at_level(logging.WARNING):
        ok, result = loader.load(xml_path, missing_requirements_strategy="ignore")
    
    assert len(caplog.records) == 1
    assert "required models are missing" in caplog.text.lower()

    assert ok is True

    ns = next(iter(result.values()))
    assert ns.uri == "urn:test:model"
    assert "i=1001" in ns.nodes_by_id


def test_alias_resolution_applied_to_reference_type_and_target(tmp_path):
    loader = make_loader(loaded_model_uris=set())

    xml_path = write_xml(
        tmp_path,
        "aliases.xml",
        f"""\
        <UANodeSet xmlns="{UA_NS}">
            <Models>
                <Model ModelUri="urn:test:model"/>
            </Models>
            <Aliases>
                <Alias Alias="HasSubtype">{HAS_SUBTYPE}</Alias>
                <Alias Alias="ParentType">{HIERARCHICAL_UA_REFS[0]}</Alias>
            </Aliases>
            <UAReferenceType NodeId="i=9001" BrowseName="0:ChildRefType">
                <References>
                    <Reference ReferenceType="HasSubtype" IsForward="false">ParentType</Reference>
                </References>
            </UAReferenceType>
        </UANodeSet>
        """,
    )

    ok, result = loader.load(xml_path)
    assert ok is True

    ns = next(iter(result.values()))
    node = ns.nodes_by_id["i=9001"]
    assert len(node.references) == 1

    r = node.references[0]
    assert r.reference_type.to_string() == HAS_SUBTYPE
    assert r.target_nodeid.to_string() == HIERARCHICAL_UA_REFS[0]
    assert r.is_forward is False


def test_classify_reference_base_hierarchical_sets_base_type_to_self(tmp_path):
    """
    A node whose node_id is the base hierarchical ref (i=33) should resolve to itself.
    """
    loader = make_loader(loaded_model_uris=set())

    xml_path = write_xml(
        tmp_path,
        "base_ref.xml",
        f"""\
        <UANodeSet xmlns="{UA_NS}">
            <Models>
                <Model ModelUri="urn:test:model"/>
            </Models>
            <UAReferenceType NodeId="{HIERARCHICAL_UA_REFS[0]}" BrowseName="0:HierarchicalReferences"/>
        </UANodeSet>
    """,
    )

    ok, result = loader.load(xml_path)
    assert ok is True

    ns = next(iter(result.values()))
    node = ns.nodes_by_id[HIERARCHICAL_UA_REFS[0]]
    assert node.base_type is not None
    assert node.base_type.to_string() == HIERARCHICAL_UA_REFS[0]


def test_classify_child_of_base_hierarchical_sets_base_type_to_own_nodeid(tmp_path):
    """
    If node has backward HasSubtype to i=33, base_type becomes node.node_id (category marker).
    """
    loader = make_loader(loaded_model_uris=set())

    xml_path = write_xml(
        tmp_path,
        "child_of_base.xml",
        f"""\
        <UANodeSet xmlns="{UA_NS}">
            <Models>
                <Model ModelUri="urn:test:model"/>
            </Models>
            <UAReferenceType NodeId="{HIERARCHICAL_UA_REFS[0]}" BrowseName="0:HierarchicalReferences"/>
            <UAReferenceType NodeId="i=1000" BrowseName="0:MyHierCategory">
                <References>
                    <Reference ReferenceType="{HAS_SUBTYPE}" IsForward="false">{HIERARCHICAL_UA_REFS[0]}</Reference>
                </References>
            </UAReferenceType>
        </UANodeSet>
        """,
    )

    ok, result = loader.load(xml_path)
    assert ok is True

    ns = next(iter(result.values()))
    child = ns.nodes_by_id["i=1000"]
    assert child.base_type is not None
    assert child.base_type.to_string() == "i=1000"


def test_load_from_file_list_defers_and_retries(tmp_path):
    """
    A.xml requires B.xml. First attempt defers A, loads B, then retries A.
    Loaded_model_uris are stored in NamespaceStub to simulate namespace context.
    """
    loaded_model_uris: set[str] = set()
    loader = make_loader(loaded_model_uris=loaded_model_uris)

    a = write_xml(
        tmp_path,
        "A.xml",
        f"""\
        <UANodeSet xmlns="{UA_NS}">
            <Models>
                <Model ModelUri="urn:A">
                    <RequiredModel ModelUri="urn:B"/>
                </Model>
            </Models>
        </UANodeSet>
        """,
    )
    b = write_xml(
        tmp_path,
        "B.xml",
        f"""\
        <UANodeSet xmlns="{UA_NS}">
            <Models>
                <Model ModelUri="urn:B"/>
            </Models>
        </UANodeSet>
        """,
            )

    out = loader.load_from_file_list([a, b])
    assert isinstance(out, dict)
    assert "urn:A" in loaded_model_uris
    assert "urn:B" in loaded_model_uris
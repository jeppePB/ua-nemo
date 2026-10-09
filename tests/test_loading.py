import logging
from pathlib import Path

import pytest

from ua_nemo import load_from_file_list, load_from_path
from ua_nemo.core import Namespace, NamespaceContext
from ua_nemo.core.exceptions import MissingRequiredModelError
from ua_nemo.parsers.loader import UA_NODESET

UA_NS = "http://opcfoundation.org/UA/2011/03/UANodeSet.xsd"
UA_URI = "http://opcfoundation.org/UA/"
UA_FILE = UA_NODESET / "Opc.Ua.NodeSet2.xml"


def write_xml(tmp_path: Path, filename: str, xml_text: str) -> Path:
    p = tmp_path / filename
    p.write_text(xml_text, encoding="utf-8")
    return p

def write_nodeset(directory: Path, filename: str, model_uri: str) -> Path:
    path = directory / filename
    path.write_text(
        f"""\
        <UANodeSet xmlns="{UA_NS}">
            <Models>
                <Model ModelUri="{model_uri}"/>
            </Models>
        </UANodeSet>
        """,
        encoding="utf-8",
    )
    return path

def test_ua_nodeset_is_loaded_first_when_not_in_file_list(tmp_path):
    a = write_nodeset(tmp_path, "A.xml", "urn:A")

    ctx = load_from_file_list([a])

    assert ctx.namespaces[0].uri == UA_URI
    assert ctx.get_namespace_by_uri("urn:A") is not None

def test_ua_nodeset_in_file_list_is_loaded_once_and_first(tmp_path):
    a = write_nodeset(tmp_path, "A.xml", "urn:A")

    ctx = load_from_file_list([a, UA_FILE])

    ua_namespaces = [ns for ns in ctx.namespaces if ns.uri == UA_URI]
    assert len(ua_namespaces) == 1
    assert ctx.namespaces[0] is ua_namespaces[0]

def test_given_context_is_used_and_returned():
    ctx = NamespaceContext()

    result = load_from_file_list([], ctx=ctx)

    assert result is ctx
    assert ctx.get_namespace_by_name("UA") is not None

def test_loading_does_not_populate_the_default_context():
    load_from_file_list([])

    assert Namespace._default_ctx is None

def test_each_call_gets_its_own_context():
    first = load_from_file_list([])
    second = load_from_file_list([])

    assert first is not second
    assert first.get_namespace_by_name("UA") is not second.get_namespace_by_name("UA")

def test_missing_files_are_skipped(tmp_path):
    ctx = load_from_file_list([tmp_path / "does-not-exist.xml"])

    assert [ns.uri for ns in ctx.namespaces] == [UA_URI]

def test_load_from_path_loads_all_xml_files_in_directory(tmp_path):
    write_nodeset(tmp_path, "A.xml", "urn:A")
    write_nodeset(tmp_path, "B.xml", "urn:B")
    (tmp_path / "notes.txt").write_text("not a nodeset", encoding="utf-8")

    ctx = load_from_path(tmp_path)

    assert ctx.get_namespace_by_uri("urn:A") is not None
    assert ctx.get_namespace_by_uri("urn:B") is not None

def test_load_from_path_accepts_str_path(tmp_path):
    write_nodeset(tmp_path, "A.xml", "urn:A")

    ctx = load_from_path(str(tmp_path))

    assert ctx.get_namespace_by_uri("urn:A") is not None

def test_load_from_file_list_defers_and_retries(tmp_path):
    """A.xml requires B.xml. First attempt defers A, loads B, then retries A."""
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

    ctx = load_from_file_list([a, b])
    assert ctx.get_namespace_by_uri("urn:A") is not None
    assert ctx.get_namespace_by_uri("urn:B") is not None

def test_load_from_file_list_defers_and_ignores(tmp_path, caplog):
    """A.xml requires B.xml, which is never provided. A is deferred until max attempts, then loaded anyway."""
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

    with caplog.at_level(logging.WARNING):
        ctx = load_from_file_list([a], handle_max_deferred_strategy="ignore")

    assert len(caplog.records) == 1
    assert "missing required model" in caplog.text.lower()
    assert ctx.get_namespace_by_uri("urn:A") is not None

def test_load_from_file_list_defers_and_raises(tmp_path, caplog):
    """A required model is never provided. After max attempts the error is logged and raised."""
    xml_path = write_xml(
        tmp_path,
        "test_model.xml",
        f"""\
        <UANodeSet xmlns="{UA_NS}">
            <Models>
                <Model ModelUri="urn:test:model" Version="1.0">
                    <RequiredModel ModelUri="urn:missing:dep1"/>
                </Model>
            </Models>
        </UANodeSet>
        """,
    )

    with caplog.at_level(logging.ERROR):
        with pytest.raises(MissingRequiredModelError) as ei:
            load_from_file_list([xml_path], handle_max_deferred_strategy="raise")

    assert len(caplog.records) == 1
    assert "failed to load required models" in caplog.text.lower()

    exc = ei.value
    assert exc.nodeset_path == xml_path
    assert exc.requesting.uri == "urn:test:model"
    assert exc.requesting.version == "1.0"

    missing_uris = [dep.uri for dep in exc.missing]
    assert missing_uris == ["urn:missing:dep1"]

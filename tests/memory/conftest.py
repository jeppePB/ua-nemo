import pytest
from pathlib import Path

NODESET_DIR = Path(__file__).parent.parent / "files/test-typelibs"

NODESETS = {
    "isa95": NODESET_DIR / "Opc.ISA95.NodeSet2.xml",
    "enttype": NODESET_DIR / "EntType.xml",
}

def nodeset_available(name: str) -> bool:
    return NODESETS[name].exists()

@pytest.fixture(scope="session")
def isa95_nodeset_path():
    if not nodeset_available("isa95"):
        pytest.skip("ISA-95 nodeset not available.")
    return NODESETS["isa95"]

@pytest.fixture(scope="session")
def enttype_nodeset_path():
    if not nodeset_available("enttype"):
        pytest.skip("enttype nodeset not available.")
    return NODESETS["enttype"]
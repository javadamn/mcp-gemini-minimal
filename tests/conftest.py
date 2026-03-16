import pytest
from pathlib import Path

from modules.seq_basics._plumbing.resolve import register_resource


@pytest.fixture(scope="session")
def pbr322_path() -> Path:
    """Path to the example GenBank file shipped with the starter."""
    return Path(__file__).parent.parent / "modules" / "seq_basics" / "data" / "pBR322.gb"


@pytest.fixture(scope="session", autouse=True)
def register_pbr322_resource(pbr322_path: Path):
    """
    Ensure the resource registry is populated for tests that use resolve_to_seq("pBR322").
    This mimics what the MCP server does at startup via auto-discovery.
    """
    register_resource("pBR322", pbr322_path)
    return True

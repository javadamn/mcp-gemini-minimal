from pathlib import Path
from modules.seq_basics._plumbing.register import register_tools, register_resources


class DummyMCP:
    """Minimal MCP stub to record what gets registered."""
    def __init__(self):
        self.tool_names = []
        self.resource_uris = []

    def tool(self, func):
        self.tool_names.append(func.__name__)
        return func

    def resource(self, uri):
        def decorator(fn):
            self.resource_uris.append(uri)
            return fn
        return decorator


def test_auto_registration_discovers_tools_and_resources():
    mcp = DummyMCP()

    base = Path(__file__).parent.parent / "modules" / "seq_basics"
    tools_dir = base / "tools"
    data_dir = base / "data"

    register_tools(mcp, tools_dir)
    register_resources(mcp, data_dir, module_name="seq_basics")

    assert "dna_translate" in mcp.tool_names
    assert "dna_reverse_complement" in mcp.tool_names
    assert "resource://seq_basics/pBR322" in mcp.resource_uris

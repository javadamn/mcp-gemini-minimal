"""Module registry for the MCP server.

We keep the server simple: it imports this file and calls `register_all(mcp)`.
"""

from __future__ import annotations

from .seq_basics import register_tools as register_seq_basics_tools
from .seq_basics import register_resources as register_seq_basics_resources
from .seq_basics import register_prompts as register_seq_basics_prompts

def register_all(mcp) -> None:
    # Starter example module (enabled by default)
    register_seq_basics_tools(mcp)
    register_seq_basics_resources(mcp)
    register_seq_basics_prompts(mcp)
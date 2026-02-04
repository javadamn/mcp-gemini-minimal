"""Tool registration for seq_basics.

This package is intentionally organized as one file per tool.
That makes it easy for teams to add/remove tools without merge conflicts.
"""

from __future__ import annotations

from .reverse_complement import register as _register_reverse_complement
from .translate import register as _register_translate

def register_tools(mcp) -> None:
    _register_reverse_complement(mcp)
    _register_translate(mcp)

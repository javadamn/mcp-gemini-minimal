"""Resource registration for seq_basics."""

from __future__ import annotations

from .pbr322_genbank import register as _register_pbr322

def register_resources(mcp) -> None:
    _register_pbr322(mcp)

"""GenBank resource: pBR322.gb"""

from __future__ import annotations

from pathlib import Path

def register(mcp) -> None:
    data_dir = Path(__file__).resolve().parents[1] / "data"

    @mcp.resource("resource://seq_basics/pbr322_genbank")
    def pbr322_genbank() -> str:
        """GenBank file for plasmid pBR322 (example resource)."""
        return (data_dir / "pBR322.gb").read_text()

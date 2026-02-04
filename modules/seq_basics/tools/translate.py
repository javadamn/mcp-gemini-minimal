"""DNA translation tool (frame 1, standard code)."""

from __future__ import annotations

from .._utils import CODON_TABLE, clean_dna

def _translate_sequence(seq: str) -> str:
    """Translate a DNA sequence (frame 1) using the standard genetic code."""
    s = clean_dna(seq)
    aa = []
    for i in range(0, len(s) - 2, 3):
        aa.append(CODON_TABLE.get(s[i:i+3], "X"))
    return "".join(aa)

def register(mcp) -> None:
    @mcp.tool
    def dna_translate(seq: str) -> str:
        """Translate a DNA sequence (frame 1) into protein using the standard code.

        Notes:
          - Uses the standard codon table.
          - Non-ACGT characters are rejected (no IUPAC ambiguity in this starter).
          - Any trailing bases not forming a full codon are ignored.
        """
        return _translate_sequence(seq)

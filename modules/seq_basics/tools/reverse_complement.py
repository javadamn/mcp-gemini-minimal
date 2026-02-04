"""Reverse-complement tools (sequence-level only)."""

from __future__ import annotations


def _reverse_complement_sequence(seq: str) -> str:
    """Compute the reverse complement of a DNA sequence string.

    Accepts A/C/G/T (case-insensitive). Whitespace is ignored.
    """
    s = "".join(seq.split()).upper()
    comp = {"A": "T", "T": "A", "C": "G", "G": "C"}

    try:
        return "".join(comp[b] for b in reversed(s))
    except KeyError as e:
        raise ValueError(f"Invalid DNA base: {e.args[0]}") from None


def register(mcp) -> None:
    @mcp.tool
    def dna_reverse_complement(seq: str) -> str:
        """Return the reverse complement of a DNA sequence.

        Input should contain only A/C/G/T (case-insensitive).
        """
        return _reverse_complement_sequence(seq)

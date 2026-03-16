import pytest
from modules.seq_basics._plumbing.resolve import resolve_to_seq


def test_resolve_raw_sequence_strips_whitespace_and_numbers():
    assert resolve_to_seq("1 ATG 2\nCGA 3 TCG") == "ATGCGATCG"


def test_resolve_fasta_string():
    fasta = ">seq1\nATGCATGC\n"
    assert resolve_to_seq(fasta) == "ATGCATGC"


def test_resolve_empty_raises():
    with pytest.raises(ValueError):
        resolve_to_seq("   ")


def test_resolve_invalid_character_raises():
    with pytest.raises(ValueError) as e:
        resolve_to_seq("ATGB")
    assert "Invalid sequence characters" in str(e.value)


def test_resolve_resource_name_pbr322():
    # relies on conftest.py autouse fixture to register resource
    seq = resolve_to_seq("pBR322")
    assert isinstance(seq, str)
    assert len(seq) > 4000  # pBR322 is 4361bp
    assert set(seq).issubset(set("ATUCGRSYKWMN"))

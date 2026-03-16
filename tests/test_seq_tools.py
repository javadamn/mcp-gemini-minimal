from modules.seq_basics.tools.translate import translate
from modules.seq_basics.tools.reverse_complement import reverse_complement
from modules.seq_basics._plumbing.resolve import resolve_to_seq


def test_reverse_complement_basic():
    assert reverse_complement("ATGC") == "GCAT"


def test_translate_basic():
    assert translate("ATGGCT") == "MA"


def test_translate_frame():
    assert translate("AATGGCT", frame=2) == "MA"


def test_resolve_raw_sequence():
    assert resolve_to_seq("ATG CGA\nTCG") == "ATGCGATCG"


def test_invalid_character():
    try:
        resolve_to_seq("ATGB")
        assert False
    except ValueError:
        assert True

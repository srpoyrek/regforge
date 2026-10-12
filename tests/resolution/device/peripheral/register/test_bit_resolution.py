"""BitResolution: one bit of a register, and how it compares with another bit.

It is given plain data, a position and a claimant's label, and knows nothing above a bit.
"""

import inspect

import regforge.resolution.device.peripheral.register.bit as bit_module
from regforge.finding import Severity
from regforge.resolution import BitResolution


def _bit(position: int, owner: str | None) -> BitResolution:
    return BitResolution(position, owner, "P.R")


def _run(owner: str, first: int, last: int) -> list[BitResolution]:
    return [_bit(position, owner) for position in range(first, last + 1)]


def _messages(findings):
    return [finding.message for finding in findings]


# --- one bit set beside another ----------------------------------------------------


def test_two_claimants_on_one_bit_are_a_warning():
    (finding,) = _bit(1, "MODE").compare(_bit(1, "STATE"))
    assert finding.severity is Severity.WARNING
    assert finding.message == "P.R: bit 1 is claimed by MODE and STATE"


def test_bits_at_different_positions_do_not_collide():
    assert _bit(1, "A").compare(_bit(2, "B")) == []


def test_an_unclaimed_bit_collides_with_nothing():
    assert _bit(1, None).compare(_bit(1, "B")) == []
    assert _bit(1, "A").compare(_bit(1, None)) == []
    assert _bit(1, None).compare(_bit(1, None)) == []


def test_the_bit_cannot_tell_two_fields_that_share_a_name_from_one():
    # Comparing different claimants is the caller's job; the bit reports what it is given.
    assert _messages(_bit(0, "Reserved").compare(_bit(0, "Reserved"))) == [
        "P.R: bit 0 is claimed by Reserved and Reserved"
    ]


def test_a_bit_alone_has_nothing_wrong():
    bit_ = _bit(3, "A")
    assert bit_.findings() == [] and str(bit_) == ""


# --- two lists of bits ---------------------------------------------------------------


def test_compare_all_pairs_the_bits_at_one_position_and_merges_a_run():
    findings = BitResolution.compare_all(_run("A", 0, 3), _run("B", 2, 5))
    assert _messages(findings) == ["P.R: bits 2..3 are claimed by A and B"]


def test_compare_all_reports_separate_runs():
    left = [_bit(0, "A"), _bit(1, "A"), _bit(5, "A")]
    right = [_bit(0, "B"), _bit(1, "B"), _bit(5, "B")]
    assert _messages(BitResolution.compare_all(left, right)) == [
        "P.R: bits 0..1 are claimed by A and B",
        "P.R: bit 5 is claimed by A and B",
    ]


def test_compare_all_does_not_depend_on_the_order_the_bits_are_given_in():
    left = [_bit(3, "A"), _bit(2, "A")]
    right = [_bit(2, "B"), _bit(3, "B")]
    assert _messages(BitResolution.compare_all(left, right)) == [
        "P.R: bits 2..3 are claimed by A and B"
    ]


def test_compare_all_is_silent_when_the_lists_share_no_position():
    assert BitResolution.compare_all(_run("A", 0, 1), _run("B", 4, 5)) == []


def test_compare_all_is_silent_for_an_empty_list():
    assert BitResolution.compare_all([], _run("B", 0, 3)) == []
    assert BitResolution.compare_all(_run("A", 0, 3), []) == []


def test_the_claimants_are_named_left_then_right():
    findings = BitResolution.compare_all(_run("STATE", 1, 1), _run("MODE", 1, 1))
    assert _messages(findings) == ["P.R: bit 1 is claimed by STATE and MODE"]


# --- layering ----------------------------------------------------------------------


def test_the_bit_class_imports_nothing_above_a_bit():
    # The layering rule: a bit knows bits. Fields and registers are the collector's business.
    source = inspect.getsource(bit_module)
    assert "regforge.ir" not in source
    assert "Field" not in source and "Register" not in source

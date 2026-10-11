"""EnumeratedValueResolution: the numbers one entry names, and how it compares with another."""

import inspect

import regforge.resolution.enumerated_value as value_module
from regforge.finding import Severity
from regforge.ir import EnumeratedValue
from regforge.resolution import EnumeratedValueResolution


def _res(entry: EnumeratedValue, width: int = 4) -> EnumeratedValueResolution:
    return EnumeratedValueResolution(entry, width, "P.R.F")


def _messages(findings):
    return [finding.message for finding in findings]


# --- the numbers an entry names ------------------------------------------------------


def test_a_plain_entry_names_one_number():
    assert _res(EnumeratedValue("A", 3)).ranges() == [(3, 3)]


def test_a_catch_all_names_none_since_it_names_the_rest():
    assert _res(EnumeratedValue("REST", None, is_default=True)).ranges() == []


def test_a_pattern_names_every_number_it_matches():
    assert _res(EnumeratedValue("P", 4, dont_care=0b11)).ranges() == [(4, 7)]


def test_a_pattern_with_a_gap_names_separate_runs():
    assert _res(EnumeratedValue("P", 0, dont_care=0b101)).ranges() == [(0, 1), (4, 5)]


def test_a_pattern_with_too_many_x_bits_is_not_expanded():
    assert _res(EnumeratedValue("P", 0, dont_care=(1 << 17) - 1), width=32).ranges() == []


def test_numbers_are_written_in_hex():
    assert EnumeratedValueResolution.write(255) == "0xff"


# --- the entry alone: a number the field cannot hold -----------------------------------


def test_a_number_the_field_cannot_hold_is_an_error():
    (finding,) = _res(EnumeratedValue("BIG", 0x14)).findings()
    assert finding.severity is Severity.ERROR
    assert finding.message == "P.R.F: BIG = 0x14 does not fit the 4-bit field"


def test_a_number_the_field_can_hold_is_silent():
    assert _res(EnumeratedValue("A", 15)).findings() == []


def test_a_pattern_reaching_past_the_field_is_an_error_named_as_written():
    findings = _res(EnumeratedValue("P", 0b10000, dont_care=0b1)).findings()
    assert _messages(findings) == ["P.R.F: P = 0b1000x does not fit the 4-bit field"]


def test_a_catch_all_always_fits():
    assert _res(EnumeratedValue("REST", None, is_default=True), width=1).findings() == []


# --- one entry set beside another ------------------------------------------------------


def test_two_entries_naming_one_number_are_a_warning():
    (finding,) = _res(EnumeratedValue("A", 1)).compare(_res(EnumeratedValue("B", 1)))
    assert finding.severity is Severity.WARNING
    assert finding.message == "P.R.F: value 0x1 is claimed by A and B"


def test_different_numbers_do_not_collide():
    assert _res(EnumeratedValue("A", 1)).compare(_res(EnumeratedValue("B", 2))) == []


def test_a_pattern_collides_with_a_number_it_matches():
    pattern, plain = _res(EnumeratedValue("P", 4, dont_care=0b11)), _res(EnumeratedValue("B", 5))
    assert _messages(pattern.compare(plain)) == ["P.R.F: value 0x5 is claimed by P and B"]


def test_two_patterns_collide_on_the_numbers_both_match():
    first = _res(EnumeratedValue("P", 0, dont_care=0b11))  # 0..3
    second = _res(EnumeratedValue("Q", 2, dont_care=0b11))  # 2..5
    assert _messages(first.compare(second)) == ["P.R.F: values 0x2..0x3 are claimed by P and Q"]


def test_a_catch_all_collides_with_nothing():
    rest = _res(EnumeratedValue("REST", None, is_default=True))
    assert rest.compare(_res(EnumeratedValue("A", 0))) == []
    assert _res(EnumeratedValue("A", 0)).compare(rest) == []


def test_two_entries_with_one_name_are_still_two_claimants():
    assert _messages(_res(EnumeratedValue("X", 3)).compare(_res(EnumeratedValue("X", 3)))) == [
        "P.R.F: value 0x3 is claimed by X and X"
    ]


# --- layering ----------------------------------------------------------------------


def test_the_value_class_knows_nothing_above_an_entry():
    source = inspect.getsource(value_module)
    for above in ("Field", "Register", "Peripheral", "Cluster", "Device", "EnumSet"):
        assert above not in source

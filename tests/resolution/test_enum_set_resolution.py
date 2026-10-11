"""EnumSetResolution: the entries of one enumerated set together, and how it compares."""

import inspect

import regforge.resolution.enum_set as set_module
from regforge.finding import Severity
from regforge.ir import EnumeratedValue, EnumSet, EnumUsage
from regforge.resolution import EnumSetResolution


def _set(*values, width=4, usage=EnumUsage.READ_WRITE, name=None) -> EnumSetResolution:
    return EnumSetResolution(EnumSet(list(values), name=name, usage=usage), width, "P.R.F")


def _messages(findings):
    return [finding.message for finding in findings]


def _plain(name, number):
    return EnumeratedValue(name, number)


def _rest(name="REST"):
    return EnumeratedValue(name, None, is_default=True)


# --- the label -----------------------------------------------------------------------


def test_a_named_set_is_called_by_its_name_and_an_unnamed_one_by_its_usage():
    assert _set(name="MODES").label == "MODES"
    assert _set(usage=EnumUsage.READ).label == "the read set"
    assert _set().label == "the read-write set"


# --- the entries one by one -----------------------------------------------------------


def test_an_entry_the_field_cannot_hold_is_an_error():
    findings = _set(_plain("BIG", 0x14)).findings()
    assert [(f.severity, f.message) for f in findings] == [
        (Severity.ERROR, "P.R.F: BIG = 0x14 does not fit the 4-bit field")
    ]


def test_every_entry_that_does_not_fit_is_reported():
    findings = _set(_plain("A", 16), _plain("B", 1), _plain("C", 17)).findings()
    assert _messages(findings) == [
        "P.R.F: A = 0x10 does not fit the 4-bit field",
        "P.R.F: C = 0x11 does not fit the 4-bit field",
    ]


# --- the entries together -------------------------------------------------------------


def test_a_name_used_twice_is_a_warning_naming_the_numbers():
    findings = _set(_plain("A", 1), _plain("A", 2)).findings()
    assert [(f.severity, f.message) for f in findings] == [
        (Severity.WARNING, "P.R.F: the name A is used by 2 entries (0x1, 0x2)")
    ]


def test_each_repeated_name_is_its_own_finding():
    entries = [_plain("A", 1), _plain("B", 2), _plain("A", 3), _plain("B", 4)]
    assert _messages(_set(*entries).names()) == [
        "P.R.F: the name A is used by 2 entries (0x1, 0x3)",
        "P.R.F: the name B is used by 2 entries (0x2, 0x4)",
    ]


def test_two_entries_naming_one_number_are_a_warning():
    findings = _set(_plain("A", 1), _plain("B", 1)).findings()
    assert _messages(findings) == ["P.R.F: value 0x1 is claimed by A and B"]


def test_three_entries_on_one_number_are_one_finding_per_pair():
    findings = _set(_plain("A", 1), _plain("B", 1), _plain("C", 1)).collisions()
    assert _messages(findings) == [
        "P.R.F: value 0x1 is claimed by A and B",
        "P.R.F: value 0x1 is claimed by A and C",
        "P.R.F: value 0x1 is claimed by B and C",
    ]


def test_a_pattern_collides_with_a_number_it_matches_whichever_comes_first():
    pattern = EnumeratedValue("P", 4, dont_care=0b11)
    assert _messages(_set(pattern, _plain("B", 5)).collisions()) == [
        "P.R.F: value 0x5 is claimed by P and B"
    ]
    assert _messages(_set(_plain("B", 5), pattern).collisions()) == [
        "P.R.F: value 0x5 is claimed by B and P"
    ]


def test_two_patterns_are_compared_once():
    first = EnumeratedValue("P", 0, dont_care=0b11)
    second = EnumeratedValue("Q", 2, dont_care=0b11)
    assert _messages(_set(first, second).collisions()) == [
        "P.R.F: values 0x2..0x3 are claimed by P and Q"
    ]


def test_distinct_numbers_and_disjoint_patterns_do_not_collide():
    pattern = EnumeratedValue("P", 8, dont_care=0b11)
    assert _set(_plain("A", 0), _plain("B", 1), pattern).collisions() == []


def test_a_catch_all_collides_with_no_number():
    assert _set(_plain("A", 0), _rest()).findings() == []


def test_two_catch_alls_are_a_warning():
    findings = _set(_rest("REST"), _rest("OTHER")).findings()
    assert [(f.severity, f.message) for f in findings] == [
        (
            Severity.WARNING,
            "P.R.F: 2 catch-all entries (REST, OTHER); only one can name the rest",
        )
    ]


def test_a_sound_set_has_nothing_to_report():
    set_ = _set(_plain("OFF", 0), _plain("ON", 1), _rest())
    assert set_.findings() == [] and str(set_) == ""


def test_an_empty_set_has_nothing_to_report():
    assert _set().findings() == []


def test_the_findings_come_in_the_order_entries_then_catch_alls_then_names_then_numbers():
    set_ = _set(_plain("A", 1), _plain("A", 1), _rest("R1"), _rest("R2"), _plain("BIG", 99))
    assert _messages(set_.findings()) == [
        "P.R.F: BIG = 0x63 does not fit the 4-bit field",
        "P.R.F: 2 catch-all entries (R1, R2); only one can name the rest",
        "P.R.F: the name A is used by 2 entries (0x1, 0x1)",
        "P.R.F: value 0x1 is claimed by A and A",
    ]


def test_a_large_set_is_not_compared_pair_by_pair():
    entries = [_plain(f"V{n}", n) for n in range(4096)]
    assert _set(*entries, width=12).findings() == []


def test_a_placeholder_name_may_repeat():
    entries = [_plain("Reserved", 8), _plain("Reserved", 9), _plain("reserved", 10)]
    entries.append(_plain("reserved", 11))
    assert _set(*entries).names() == []
    assert _set(*entries).findings() == []


def test_a_real_name_repeated_beside_placeholders_is_still_reported():
    entries = [_plain("Reserved", 8), _plain("ON", 1), _plain("Reserved", 9), _plain("ON", 2)]
    assert _messages(_set(*entries).names()) == [
        "P.R.F: the name ON is used by 2 entries (0x1, 0x2)"
    ]


def test_placeholders_still_collide_on_a_number():
    findings = _set(_plain("Reserved", 8), _plain("Reserved", 8)).findings()
    assert _messages(findings) == ["P.R.F: value 0x8 is claimed by Reserved and Reserved"]


# --- one set beside another -----------------------------------------------------------


def test_two_sets_describing_one_direction_are_a_warning():
    first = _set(usage=EnumUsage.READ, name="A")
    second = _set(usage=EnumUsage.READ, name="B")
    (finding,) = first.compare(second)
    assert finding.severity is Severity.WARNING
    assert finding.message == "P.R.F: A and B both describe reads"


def test_a_read_set_and_a_write_set_are_fine_together():
    assert _set(usage=EnumUsage.READ).compare(_set(usage=EnumUsage.WRITE)) == []


def test_a_read_write_set_clashes_with_a_read_set():
    findings = _set(usage=EnumUsage.READ_WRITE).compare(_set(usage=EnumUsage.READ))
    assert _messages(findings) == ["P.R.F: the read-write set and the read set both describe reads"]


# --- layering ----------------------------------------------------------------------


def test_the_set_class_knows_nothing_above_a_set():
    source = inspect.getsource(set_module)
    for above in ("Field", "Register", "Peripheral", "Cluster", "Device"):
        assert above not in source

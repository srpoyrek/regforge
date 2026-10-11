"""FieldResolution: one field of a register, where it sits and how it compares with another."""

import inspect

import pytest

import regforge.resolution.field as field_module
from regforge.finding import Severity
from regforge.ir import Dim, Field
from regforge.resolution import BitResolution, FieldResolution


def _res(field: Field, width: int = 8) -> FieldResolution:
    return FieldResolution(field, width, "P.R")


def _messages(findings):
    return [finding.message for finding in findings]


# --- what the field occupies ---------------------------------------------------------


def test_a_field_occupies_the_bits_of_its_range():
    assert _res(Field("A", 2, 3)).ranges() == [(2, 4)]


def test_an_array_occupies_a_run_per_copy():
    assert _res(Field("OD", 0, 1, dim=Dim(4, 2, array=True))).ranges() == [
        (0, 0),
        (2, 2),
        (4, 4),
        (6, 6),
    ]


def test_runs_are_cut_off_at_the_register_width():
    assert _res(Field("A", 6, 4)).ranges() == [(6, 7)]
    assert _res(Field("B", 9, 2)).ranges() == []


def test_the_bits_are_one_per_position_with_the_field_as_claimant():
    bits = _res(Field("A", 2, 3)).bits()
    assert [bit.position for bit in bits] == [2, 3, 4]
    assert {bit.owner for bit in bits} == {"A"}
    assert all(isinstance(bit, BitResolution) and bit.where == "P.R" for bit in bits)


def test_an_array_is_labelled_with_its_count():
    assert _res(Field("OD", 0, 1, dim=Dim(4, 2, array=True))).owner == "OD[4]"


def test_the_bits_of_an_array_overlapping_itself_are_listed_once():
    bits = _res(Field("A", 0, 4, dim=Dim(2, 2, array=True))).bits()
    assert [bit.position for bit in bits] == [0, 1, 2, 3, 4, 5]


# --- the field alone: past the register's width ---------------------------------------


def test_a_field_past_the_register_width_is_an_error():
    (finding,) = _res(Field("F", 30, 4), width=32).findings()
    assert finding.severity is Severity.ERROR
    assert finding.message == "P.R.F: bits 30..33 run past the 32-bit register"


def test_an_array_is_measured_to_its_last_copy():
    resolution = _res(Field("A", 0, 4, dim=Dim(9, 4, array=True)), width=32)
    assert _messages(resolution.findings()) == ["P.R.A[9]: bits 0..35 run past the 32-bit register"]


def test_a_field_reaching_exactly_the_last_bit_fits():
    assert _res(Field("A", 28, 4), width=32).findings() == []


def test_one_bit_too_many_is_past_the_width():
    assert _messages(_res(Field("A", 29, 4), width=32).findings()) == [
        "P.R.A: bits 29..32 run past the 32-bit register"
    ]


def test_a_copy_of_a_template_alone_is_left_to_check_all():
    assert _res(Field("M8", 32, 4, expanded_from="M%s"), width=32).findings() == []


def test_str_is_the_report():
    assert str(_res(Field("F", 6, 4))) == "error: P.R.F: bits 6..9 run past the 8-bit register"
    assert str(_res(Field("F", 0, 4))) == ""


# --- a register's fields: copies of a template are one finding --------------------------


def test_fields_past_the_register_width_are_errors_collapsed_per_template():
    fields = [
        Field("F", 30, 4),  # a plain field: bits 30..33
        Field("A", 0, 4, dim=Dim(9, 4, array=True)),  # an array: 9 x 4 bits reach 36
        *[Field(f"M{i}", 4 * i, 4, expanded_from="M%s") for i in range(9)],  # M8 at 32..35
    ]
    findings = FieldResolution.check_all([_res(field, width=32) for field in fields])
    assert {finding.severity for finding in findings} == {Severity.ERROR}
    assert _messages(findings) == [
        "P.R.F: bits 30..33 run past the 32-bit register",
        "P.R.A[9]: bits 0..35 run past the 32-bit register",
        "P.R.M%s: M8..M8 (1 of its 9 copies) run past the 32-bit register",
    ]


def test_copies_that_fit_are_counted_in_the_total():
    fields = [Field(f"M{i}", 4 * i, 4, expanded_from="M%s") for i in range(4)]
    findings = FieldResolution.check_all([_res(field, width=8) for field in fields])
    assert _messages(findings) == [
        "P.R.M%s: M2..M3 (2 of its 4 copies) run past the 8-bit register"
    ]


def test_single_findings_come_before_the_template_ones():
    fields = [Field("M2", 8, 4, expanded_from="M%s"), Field("F", 6, 4)]
    findings = FieldResolution.check_all([_res(field) for field in fields])
    assert _messages(findings) == [
        "P.R.F: bits 6..9 run past the 8-bit register",
        "P.R.M%s: M2..M2 (1 of its 1 copies) run past the 8-bit register",
    ]


def test_a_register_with_nothing_wrong_has_nothing_to_report():
    fields = [Field("A", 0, 4), Field("B", 4, 4)]
    assert FieldResolution.check_all([_res(field) for field in fields]) == []


# --- one field set beside another --------------------------------------------------


def test_two_fields_on_one_bit_are_a_warning():
    (finding,) = _res(Field("MODE", 0, 2)).compare(_res(Field("STATE", 1, 2)))
    assert finding.severity is Severity.WARNING
    assert finding.message == "P.R: bit 1 is claimed by MODE and STATE"


def test_a_run_of_shared_bits_is_one_finding():
    findings = _res(Field("A", 0, 8), 16).compare(_res(Field("B", 4, 8), 16))
    assert _messages(findings) == ["P.R: bits 4..7 are claimed by A and B"]


def test_fields_that_only_touch_do_not_collide():
    assert _res(Field("A", 0, 2)).compare(_res(Field("B", 2, 2))) == []


def test_fields_far_apart_do_not_collide():
    assert _res(Field("A", 0, 2)).compare(_res(Field("B", 6, 2))) == []


def test_copies_of_one_template_are_not_compared_with_each_other():
    first = _res(Field("M0", 0, 3, expanded_from="M%s"))
    second = _res(Field("M1", 2, 3, expanded_from="M%s"))
    assert first.compare(second) == []


def test_a_copy_is_compared_with_a_field_of_another_origin():
    copy = _res(Field("M0", 0, 3, expanded_from="M%s"))
    assert _messages(copy.compare(_res(Field("X", 1, 1)))) == ["P.R: bit 1 is claimed by M0 and X"]


def test_copies_of_different_templates_are_compared():
    first = _res(Field("M0", 0, 3, expanded_from="M%s"))
    second = _res(Field("N0", 2, 3, expanded_from="N%s"))
    assert _messages(first.compare(second)) == ["P.R: bit 2 is claimed by M0 and N0"]


def test_two_fields_that_share_a_name_are_still_two_claimants():
    findings = _res(Field("Reserved", 0, 4)).compare(_res(Field("Reserved", 2, 4)))
    assert _messages(findings) == ["P.R: bits 2..3 are claimed by Reserved and Reserved"]


def test_bits_beyond_the_register_are_not_a_collision():
    assert _res(Field("A", 6, 4)).compare(_res(Field("B", 8, 4))) == []


def test_an_array_is_named_with_its_count():
    array = _res(Field("OD", 0, 1, dim=Dim(4, 1, array=True)))
    assert _messages(array.compare(_res(Field("X", 1, 1)))) == [
        "P.R: bit 1 is claimed by OD[4] and X"
    ]


def test_the_field_compared_is_named_first():
    findings = _res(Field("B", 0, 1)).compare(_res(Field("A", 0, 1)))
    assert _messages(findings) == ["P.R: bit 0 is claimed by B and A"]


def test_the_bit_class_judges_the_shared_bits():
    first, second = _res(Field("A", 0, 4)), _res(Field("B", 2, 4))
    assert first.compare(second) == BitResolution.compare_all(first.bits(), second.bits())


def test_a_field_is_compared_only_with_another_field():
    with pytest.raises(TypeError, match="another field"):
        _res(Field("A", 0, 1)).compare(BitResolution(0, "B", "P.R"))


# --- layering ----------------------------------------------------------------------


def test_the_field_class_knows_nothing_above_a_field():
    source = inspect.getsource(field_module)
    for above in ("Register", "Peripheral", "Cluster", "Device"):
        assert above not in source

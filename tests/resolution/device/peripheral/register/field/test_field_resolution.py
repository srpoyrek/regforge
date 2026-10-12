"""FieldResolution: one field of a register, where it sits and how it compares with another."""

import inspect

import pytest

import regforge.resolution.device.peripheral.register.field.field as field_module
from regforge.finding import Severity
from regforge.ir import (
    Access,
    Dim,
    EnumeratedValue,
    EnumSet,
    EnumUsage,
    Field,
    ModifiedWriteValues,
    ReadAction,
)
from regforge.resolution import (
    BitResolution,
    FieldResolution,
    ModifiedWriteValuesResolution,
    ReadActionResolution,
)


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


# --- two fields with one name -----------------------------------------------------------


def test_two_fields_with_one_name_are_a_warning():
    (finding,) = _res(Field("MODE", 0, 2)).compare(_res(Field("MODE", 4, 2)))
    assert finding.severity is Severity.WARNING
    assert finding.message == "P.R: the name MODE is used by two fields (bits 0..1 and bits 4..5)"


def test_the_two_fields_are_placed_in_the_order_compared():
    findings = _res(Field("X", 6, 2)).compare(_res(Field("X", 0, 2)))
    assert _messages(findings) == [
        "P.R: the name X is used by two fields (bits 6..7 and bits 0..1)"
    ]


def test_a_single_bit_is_placed_as_one_bit():
    findings = _res(Field("EN", 0, 1)).compare(_res(Field("EN", 7, 1)))
    assert _messages(findings) == ["P.R: the name EN is used by two fields (bit 0 and bit 7)"]


def test_an_array_is_placed_from_its_first_bit_to_its_last_copy():
    array = _res(Field("OD", 0, 1, dim=Dim(4, 2, array=True)))  # bits 0, 2, 4 and 6
    assert _messages(array.compare(_res(Field("OD", 7, 1)))) == [
        "P.R: the name OD is used by two fields (bits 0..6 and bit 7)"
    ]


def test_the_places_named_are_as_declared_even_past_the_register_width():
    findings = _res(Field("A", 6, 4)).compare(_res(Field("A", 8, 4)))
    assert _messages(findings) == [
        "P.R: the name A is used by two fields (bits 6..9 and bits 8..11)"
    ]


def test_different_names_are_not_a_clash():
    assert _res(Field("A", 0, 2)).compare(_res(Field("B", 4, 2))) == []


def test_names_are_compared_as_written():
    assert _res(Field("Mode", 0, 2)).compare(_res(Field("MODE", 4, 2))) == []


def test_a_placeholder_name_may_repeat():
    assert _res(Field("Reserved", 0, 2)).compare(_res(Field("Reserved", 4, 2))) == []
    assert _res(Field("RESERVED_", 0, 2)).compare(_res(Field("RESERVED_", 4, 2))) == []


def test_a_field_called_reserved_is_a_placeholder():
    assert _res(Field("Reserved", 0, 2)).is_placeholder()
    assert not _res(Field("MODE", 0, 2)).is_placeholder()


def test_one_name_on_one_bit_is_two_findings_the_name_first():
    findings = _res(Field("X", 0, 4)).compare(_res(Field("X", 2, 4)))
    assert _messages(findings) == [
        "P.R: the name X is used by two fields (bits 0..3 and bits 2..5)",
        "P.R: bits 2..3 are claimed by X and X",
    ]


def test_copies_of_one_template_are_not_compared_for_names_either():
    first = _res(Field("M0", 0, 2, expanded_from="M%s"))
    second = _res(Field("M0", 4, 2, expanded_from="M%s"))
    assert first.compare(second) == []


def test_a_copy_and_a_field_of_another_origin_with_one_name_are_reported():
    copy = _res(Field("M0", 0, 2, expanded_from="M%s"))
    assert _messages(copy.compare(_res(Field("M0", 4, 2)))) == [
        "P.R: the name M0 is used by two fields (bits 0..1 and bits 4..5)"
    ]


# --- the field's enumerated sets ------------------------------------------------------


def _with_sets(*sets: EnumSet, name: str = "F", **field_args) -> Field:
    return Field(name, 0, 2, enum_sets=list(sets), **field_args)


def test_a_field_without_sets_has_no_enum_findings():
    assert _res(Field("F", 0, 2)).enum_findings() == []


def test_a_name_used_twice_in_a_set_is_reported_at_the_fields_path():
    field = _with_sets(EnumSet([EnumeratedValue("A", 1), EnumeratedValue("A", 2)]))
    assert _messages(_res(field).findings()) == [
        "P.R.F: the name A is used by 2 entries (0x1, 0x2)"
    ]


def test_the_sets_are_judged_against_the_fields_width_not_the_registers():
    field = _with_sets(EnumSet([EnumeratedValue("BIG", 5)]))  # fits an 8-bit register, not 2 bits
    assert _messages(_res(field, width=8).findings()) == [
        "P.R.F: BIG = 0x5 does not fit the 2-bit field"
    ]


def test_two_sets_describing_one_direction_are_reported_for_the_pair():
    field = _with_sets(
        EnumSet([EnumeratedValue("A", 0)], name="FIRST", usage=EnumUsage.READ),
        EnumSet([EnumeratedValue("B", 0)], name="SECOND", usage=EnumUsage.READ),
    )
    assert _messages(_res(field).findings()) == ["P.R.F: FIRST and SECOND both describe reads"]


def test_a_read_set_and_a_write_set_are_fine():
    field = _with_sets(
        EnumSet([EnumeratedValue("A", 0)], usage=EnumUsage.READ),
        EnumSet([EnumeratedValue("A", 0)], usage=EnumUsage.WRITE),
    )
    assert _res(field).findings() == []


def test_an_array_names_the_path_with_its_count():
    field = _with_sets(
        EnumSet([EnumeratedValue("A", 1), EnumeratedValue("A", 2)]),
        name="OD",
        dim=Dim(4, 2, array=True),
    )
    assert _messages(_res(field).findings()) == [
        "P.R.OD[4]: the name A is used by 2 entries (0x1, 0x2)"
    ]


def test_the_width_finding_comes_before_the_enum_findings():
    field = Field(
        "F", 6, 4, enum_sets=[EnumSet([EnumeratedValue("A", 1), EnumeratedValue("A", 2)])]
    )
    assert _messages(_res(field).findings()) == [
        "P.R.F: bits 6..9 run past the 8-bit register",
        "P.R.F: the name A is used by 2 entries (0x1, 0x2)",
    ]


def test_each_copy_of_a_template_has_its_own_sets_judged():
    def copy(name: str) -> Field:
        entries = [EnumeratedValue("A", 1), EnumeratedValue("A", 2)]
        return Field(name, 0, 2, enum_sets=[EnumSet(list(entries))], expanded_from="M%s")

    findings = FieldResolution.check_all([_res(copy("M0")), _res(copy("M1"))])
    assert _messages(findings) == [
        "P.R.M0: the name A is used by 2 entries (0x1, 0x2)",
        "P.R.M1: the name A is used by 2 entries (0x1, 0x2)",
    ]


# --- the field's write behaviour and read action ---------------------------------------


def test_a_write_behaviour_on_a_read_only_field_is_reported_at_the_fields_path():
    field = Field(
        "DONE",
        0,
        1,
        access=Access.READ_ONLY,
        modified_write_values=ModifiedWriteValues.ONE_TO_CLEAR,
    )
    assert _messages(_res(field).findings()) == [
        "P.R.DONE: modifiedWriteValues oneToClear describes a write, but access is read-only"
    ]


def test_a_read_action_on_a_write_only_field_is_reported_at_the_fields_path():
    field = Field("DATA", 0, 8, access=Access.WRITE_ONLY, read_action=ReadAction.CLEAR)
    assert _messages(_res(field).findings()) == [
        "P.R.DATA: readAction clear describes a read, but access is write-only"
    ]


def test_a_read_to_clear_flag_that_is_also_write_one_to_clear_is_fine():
    field = Field(
        "FLAG",
        0,
        1,
        access=Access.READ_WRITE,
        modified_write_values=ModifiedWriteValues.ONE_TO_CLEAR,
        read_action=ReadAction.CLEAR,
    )
    assert _res(field).effect_findings() == []


def test_a_field_with_an_unresolved_access_is_not_a_contradiction():
    field = Field("F", 0, 1, modified_write_values=ModifiedWriteValues.CLEAR)
    assert _res(field).effect_findings() == []


def test_the_write_behaviour_is_judged_before_the_read_action():
    field = Field(
        "F",
        0,
        1,
        modified_write_values=ModifiedWriteValues.SET,
        read_action=ReadAction.SET,
    )
    kinds = [type(effect) for effect in _res(field).effects()]
    assert kinds == [ModifiedWriteValuesResolution, ReadActionResolution]


def test_a_field_with_neither_has_no_effects():
    assert _res(Field("F", 0, 1)).effects() == []


def test_an_array_names_the_path_with_its_count_for_its_effects():
    field = Field(
        "OD",
        0,
        1,
        access=Access.READ_ONLY,
        dim=Dim(4, 2, array=True),
        modified_write_values=ModifiedWriteValues.CLEAR,
    )
    assert _messages(_res(field).findings()) == [
        "P.R.OD[4]: modifiedWriteValues clear describes a write, but access is read-only"
    ]


def test_the_width_and_the_sets_are_reported_before_the_effects():
    field = Field(
        "F",
        6,
        4,
        access=Access.READ_ONLY,
        modified_write_values=ModifiedWriteValues.ONE_TO_CLEAR,
        enum_sets=[EnumSet([EnumeratedValue("A", 1), EnumeratedValue("A", 2)])],
    )
    assert _messages(_res(field).findings()) == [
        "P.R.F: bits 6..9 run past the 8-bit register",
        "P.R.F: the name A is used by 2 entries (0x1, 0x2)",
        "P.R.F: modifiedWriteValues oneToClear describes a write, but access is read-only",
    ]


def test_each_copy_of_a_template_has_its_effects_judged():
    def copy(name: str) -> Field:
        return Field(
            name,
            0,
            1,
            access=Access.READ_ONLY,
            modified_write_values=ModifiedWriteValues.ONE_TO_SET,
            expanded_from="M%s",
        )

    findings = FieldResolution.check_all([_res(copy("M0")), _res(copy("M1"))])
    assert _messages(findings) == [
        "P.R.M0: modifiedWriteValues oneToSet describes a write, but access is read-only",
        "P.R.M1: modifiedWriteValues oneToSet describes a write, but access is read-only",
    ]


# --- the field's access beside its register's -------------------------------------------


def _within(field: Field, register_access: Access | None, width: int = 8) -> FieldResolution:
    return FieldResolution(field, width, "P.R", register_access)


def test_a_field_that_can_be_written_in_a_read_only_register_is_reported():
    field = Field("F", 0, 1, access=Access.READ_WRITE)
    assert _messages(_within(field, Access.READ_ONLY).findings()) == [
        "P.R.F: access is read-write, but its register is read-only"
    ]


def test_a_field_with_a_narrower_access_than_its_register_is_fine():
    field = Field("F", 0, 1, access=Access.READ_ONLY)
    assert _within(field, Access.READ_WRITE).findings() == []


def test_a_field_with_no_register_access_to_compare_with_is_fine():
    assert _res(Field("F", 0, 1, access=Access.READ_WRITE)).findings() == []


def test_an_array_names_the_path_with_its_count_for_its_access():
    field = Field("OD", 0, 1, access=Access.WRITE_ONLY, dim=Dim(4, 2, array=True))
    assert _messages(_within(field, Access.READ_ONLY).findings()) == [
        "P.R.OD[4]: access is write-only, but its register is read-only"
    ]


def test_the_sets_of_a_field_are_judged_against_its_own_access():
    write_set = EnumSet([EnumeratedValue("A", 1)], usage=EnumUsage.WRITE)
    field = Field("F", 0, 2, access=Access.READ_ONLY, enum_sets=[write_set])
    assert _messages(_res(field).findings()) == [
        "P.R.F: the write set describes writes, but access is read-only"
    ]


def test_the_width_is_reported_first_then_the_access_then_the_sets_then_the_effects():
    field = Field(
        "F",
        6,
        4,
        access=Access.WRITE_ONLY,
        read_action=ReadAction.CLEAR,
        enum_sets=[EnumSet([EnumeratedValue("A", 1), EnumeratedValue("A", 2)])],
    )
    assert _messages(_within(field, Access.READ_ONLY).findings()) == [
        "P.R.F: bits 6..9 run past the 8-bit register",
        "P.R.F: access is write-only, but its register is read-only",
        "P.R.F: the name A is used by 2 entries (0x1, 0x2)",
        "P.R.F: readAction clear describes a read, but access is write-only",
    ]


def test_the_content_findings_leave_the_width_to_check_all():
    field = Field("F", 6, 4, access=Access.READ_WRITE)
    assert _messages(_within(field, Access.READ_ONLY).content_findings()) == [
        "P.R.F: access is read-write, but its register is read-only"
    ]


def test_check_all_asks_every_field_for_its_access_a_copy_of_a_template_included():
    def copy(name: str) -> Field:
        return Field(name, 0, 1, access=Access.READ_WRITE, expanded_from="M%s")

    fields = [
        _within(Field("F", 0, 1, access=Access.READ_WRITE), Access.READ_ONLY),
        _within(copy("M0"), Access.READ_ONLY),
        _within(copy("M1"), Access.READ_ONLY),
    ]
    assert _messages(FieldResolution.check_all(fields)) == [
        "P.R.F: access is read-write, but its register is read-only",
        "P.R.M0: access is read-write, but its register is read-only",
        "P.R.M1: access is read-write, but its register is read-only",
    ]


# --- layering ----------------------------------------------------------------------


def test_the_field_class_knows_nothing_above_a_field():
    source = inspect.getsource(field_module)
    for above in ("Register", "Peripheral", "Cluster", "Device"):
        assert above not in source

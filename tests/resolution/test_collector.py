"""collect: the one place that knows the device; it feeds the bit class and gathers findings."""

from regforge.finding import Finding, Severity
from regforge.ir import (
    Access,
    Cluster,
    DataType,
    Device,
    Dim,
    EnumeratedValue,
    EnumSet,
    Field,
    ModifiedWriteValues,
    Peripheral,
    ReadAction,
    Register,
)
from regforge.resolution import collect


def _colliding(name: str) -> Register:
    return Register(name, 0, size=8, fields=[Field("A", 0, 2), Field("B", 1, 2)])


def _device(*fields: Field, size: int | None = 8) -> Device:
    register = Register("R", 0, size=size, fields=list(fields))
    return Device(name="Chip", peripherals=[Peripheral("P", 0, registers=[register])])


def _messages(device: Device) -> list[str]:
    return [finding.message for finding in collect(device)]


def test_a_clean_device_has_no_findings(demo_device):
    assert collect(demo_device) == []


def test_findings_name_registers_by_their_dotted_path():
    inner = Cluster("SUB", 0x20, registers=[_colliding("DEEP")])
    outer = Cluster("CH", 0x10, registers=[_colliding("C")], clusters=[inner])
    peripheral = Peripheral("P", 0, registers=[_colliding("R")], clusters=[outer])
    findings = collect(Device(name="Chip", peripherals=[peripheral]))
    assert [finding.message for finding in findings] == [
        "P.R: bit 1 is claimed by A and B",
        "P.CH.C: bit 1 is claimed by A and B",
        "P.CH.SUB.DEEP: bit 1 is claimed by A and B",
    ]


def test_every_peripheral_is_walked():
    first = Peripheral("ONE", 0, registers=[_colliding("R")])
    second = Peripheral("TWO", 0x100, registers=[_colliding("R")])
    findings = collect(Device(name="Chip", peripherals=[first, second]))
    assert [finding.message.split(":")[0] for finding in findings] == ["ONE.R", "TWO.R"]


def test_the_result_is_a_list_of_warnings():
    findings = collect(_device(Field("A", 0, 2), Field("B", 1, 2)))
    assert all(isinstance(finding, Finding) for finding in findings)
    assert {finding.severity for finding in findings} == {Severity.WARNING}


def test_a_run_of_shared_bits_is_one_finding():
    assert _messages(_device(Field("A", 0, 8), Field("B", 4, 8), size=16)) == [
        "P.R: bits 4..7 are claimed by A and B"
    ]


def test_separate_runs_are_separate_findings():
    device = _device(Field("A", 0, 8), Field("B", 0, 1), Field("C", 6, 2))
    assert _messages(device) == [
        "P.R: bit 0 is claimed by A and B",
        "P.R: bits 6..7 are claimed by A and C",
    ]


def test_three_claimants_on_a_bit_are_one_finding_per_pair():
    device = _device(Field("A", 0, 4), Field("B", 2, 4), Field("C", 3, 1))
    assert _messages(device) == [
        "P.R: bits 2..3 are claimed by A and B",
        "P.R: bit 3 is claimed by A and C",
        "P.R: bit 3 is claimed by B and C",
    ]


def test_two_fields_that_share_a_name_are_still_two_claimants():
    assert _messages(_device(Field("Reserved", 0, 4), Field("Reserved", 2, 4))) == [
        "P.R: bits 2..3 are claimed by Reserved and Reserved"
    ]


def test_a_field_array_is_named_with_its_count():
    device = _device(Field("OD", 0, 1, dim=Dim(4, 1, array=True)), Field("X", 1, 1))
    assert _messages(device) == ["P.R: bit 1 is claimed by OD[4] and X"]


def test_a_field_array_overlapping_itself_is_one_claimant():
    # check_address_math reports an array whose stride is smaller than its field.
    assert _messages(_device(Field("A", 0, 4, dim=Dim(2, 2, array=True)))) == []


def test_copies_of_one_template_overlapping_each_other_are_left_to_expansion():
    device = _device(Field("M0", 0, 3, expanded_from="M%s"), Field("M1", 2, 3, expanded_from="M%s"))
    assert _messages(device) == []


def test_a_copy_colliding_with_a_field_of_another_origin_is_reported():
    device = _device(Field("M0", 0, 3, expanded_from="M%s"), Field("X", 1, 1))
    assert _messages(device) == ["P.R: bit 1 is claimed by M0 and X"]


def test_fields_that_only_touch_do_not_collide():
    assert _messages(_device(Field("A", 0, 2), Field("B", 2, 2))) == []


def test_bits_beyond_the_register_are_not_a_collision():
    # Both fields run past an 8-bit register: two errors, no collision on bits that do not exist.
    assert _messages(_device(Field("A", 6, 4), Field("B", 8, 4))) == [
        "P.R.A: bits 6..9 run past the 8-bit register",
        "P.R.B: bits 8..11 run past the 8-bit register",
    ]


def test_a_field_past_the_register_width_is_an_error():
    findings = collect(_device(Field("F", 6, 4)))
    assert [(f.severity, f.message) for f in findings] == [
        (Severity.ERROR, "P.R.F: bits 6..9 run past the 8-bit register")
    ]


def test_a_register_with_no_resolved_size_is_skipped():
    assert _messages(_device(Field("A", 0, 2), Field("B", 1, 2), size=None)) == []


def test_the_enumerated_sets_of_a_field_are_judged_too():
    entries = [EnumeratedValue("A", 1), EnumeratedValue("A", 2), EnumeratedValue("BIG", 9)]
    device = _device(Field("MODE", 0, 2, enum_sets=[EnumSet(entries)]))
    assert _messages(device) == [
        "P.R.MODE: BIG = 0x9 does not fit the 2-bit field",
        "P.R.MODE: the name A is used by 2 entries (0x1, 0x2)",
    ]


def test_a_register_whose_fields_are_sound_has_no_findings():
    device = _device(Field("EN", 0, 1, enum_sets=[EnumSet([EnumeratedValue("OFF", 0)])]))
    assert _messages(device) == []


def test_two_fields_with_one_name_are_reported_even_when_their_bits_are_apart():
    assert _messages(_device(Field("MODE", 0, 2), Field("MODE", 4, 2))) == [
        "P.R: the name MODE is used by two fields (bits 0..1 and bits 4..5)"
    ]


def test_a_name_used_three_times_is_one_finding_per_pair():
    device = _device(Field("X", 0, 1), Field("X", 2, 1), Field("X", 4, 1))
    assert _messages(device) == [
        "P.R: the name X is used by two fields (bit 0 and bit 2)",
        "P.R: the name X is used by two fields (bit 0 and bit 4)",
        "P.R: the name X is used by two fields (bit 2 and bit 4)",
    ]


def test_a_register_may_repeat_reserved_fields():
    device = _device(Field("Reserved", 0, 2), Field("Reserved", 3, 2), Field("Reserved", 6, 2))
    assert _messages(device) == []


def test_a_set_may_repeat_reserved_entries():
    entries = [EnumeratedValue("Reserved", 2), EnumeratedValue("Reserved", 3)]
    assert _messages(_device(Field("MODE", 0, 2, enum_sets=[EnumSet(entries)]))) == []


def _of(register: Register) -> list[str]:
    device = Device(name="Chip", peripherals=[Peripheral("P", 0, registers=[register])])
    return [finding.message for finding in collect(device)]


def test_the_write_behaviour_of_a_register_is_judged_against_its_access():
    register = Register(
        "R",
        0,
        size=8,
        access=Access.READ_ONLY,
        modified_write_values=ModifiedWriteValues.ONE_TO_SET,
    )
    assert _of(register) == [
        "P.R: modifiedWriteValues oneToSet describes a write, but access is read-only"
    ]


def test_the_read_action_of_a_register_is_judged_against_its_access():
    register = Register(
        "R", 0, size=8, access=Access.WRITE_ONLY, read_action=ReadAction.MODIFY_EXTERNAL
    )
    assert _of(register) == [
        "P.R: readAction modifyExternal describes a read, but access is write-only"
    ]


def test_a_field_is_judged_against_its_own_access_not_the_registers():
    field = Field(
        "F", 0, 1, access=Access.READ_ONLY, modified_write_values=ModifiedWriteValues.CLEAR
    )
    register = Register("R", 0, size=8, access=Access.READ_WRITE, fields=[field])
    assert _of(register) == [
        "P.R.F: modifiedWriteValues clear describes a write, but access is read-only"
    ]


def test_the_registers_own_effects_come_before_those_of_its_fields():
    field = Field(
        "F", 0, 1, access=Access.READ_ONLY, modified_write_values=ModifiedWriteValues.CLEAR
    )
    register = Register(
        "R",
        0,
        size=8,
        access=Access.READ_ONLY,
        modified_write_values=ModifiedWriteValues.CLEAR,
        fields=[field],
    )
    assert [message.split(":")[0] for message in _of(register)] == ["P.R", "P.R.F"]


def test_effects_that_agree_with_the_access_are_silent():
    register = Register("R", 0, size=8, access=Access.READ_ONLY, read_action=ReadAction.CLEAR)
    assert _of(register) == []


def test_a_register_with_no_resolved_size_has_no_effects_judged():
    register = Register(
        "R", 0, access=Access.READ_ONLY, modified_write_values=ModifiedWriteValues.CLEAR
    )
    assert _of(register) == []


def test_a_field_is_judged_against_the_access_of_its_register():
    field = Field("F", 0, 1, access=Access.READ_WRITE)
    register = Register("R", 0, size=8, access=Access.READ_ONLY, fields=[field])
    assert _of(register) == ["P.R.F: access is read-write, but its register is read-only"]


def test_a_data_type_of_another_width_than_the_register_is_reported():
    register = Register("R", 0, size=32, data_type=DataType.UINT16)
    assert _of(register) == ["P.R: dataType uint16_t is 16 bits wide, but the register is 32 bits"]


def test_a_data_type_as_wide_as_the_register_is_fine():
    assert _of(Register("R", 0, size=32, data_type=DataType.UINT32)) == []


def test_a_pointer_data_type_is_not_compared_with_the_register_size():
    assert _of(Register("R", 0, size=32, data_type=DataType.UINT8_PTR)) == []

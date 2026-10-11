"""collect: the one place that knows the device; it feeds the bit class and gathers findings."""

from regforge.finding import Finding, Severity
from regforge.ir import (
    Cluster,
    Device,
    Dim,
    EnumeratedValue,
    EnumSet,
    Field,
    Peripheral,
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

"""expand_dim leaves every unrolled copy with its origin, so the array can be read back."""

from regforge.ir import Device, Dim, Field, Peripheral, Register, array_groups, compact
from regforge.resolve import expand_dim


def _expanded() -> Device:
    pwm = Peripheral(
        "PWM%s",
        0x1000,
        dim=Dim(2, 0x100, index=["A", "B"]),
        registers=[
            Register(
                "DT%s",
                0x20,
                size=32,
                dim=Dim(2, 8),
                fields=[Field("F%s", 0, 1, dim=Dim(2, 2))],
            )
        ],
    )
    device = Device(name="X", peripherals=[pwm])
    expand_dim(device)
    return device


def test_unrolled_peripherals_remember_their_template_label_and_place():
    first, second = _expanded().peripherals
    assert (first.name, second.name) == ("PWMA", "PWMB")
    assert first.origin is not None and second.origin is not None
    assert (first.origin.template, first.origin.label, first.origin.index) == ("PWM%s", "A", 0)
    assert (second.origin.label, second.origin.index) == ("B", 1)
    assert first.origin.count == 2 and first.origin.dim.stride == 0x100
    assert first.expanded_from == first.origin.template


def test_unrolled_registers_remember_where_in_the_array_they_sit():
    registers = _expanded().peripherals[0].registers
    assert [r.name for r in registers] == ["DT0", "DT1"]
    origins = [r.origin for r in registers]
    assert all(o is not None for o in origins)
    assert [o.index for o in origins if o] == [0, 1]
    assert [r.address_offset for r in registers] == [0x20 + o.offset for o in origins if o]


def test_unrolled_fields_remember_their_origin_too():
    fields = _expanded().peripherals[0].registers[0].fields
    assert [f.name for f in fields] == ["F0", "F1"]
    assert [f.origin.index for f in fields if f.origin] == [0, 1]


def test_the_array_is_read_back_from_the_elaborated_tree():
    device = _expanded()
    (group,) = array_groups(device.peripherals)
    assert group.template == "PWM%s" and group.names == ("PWMA", "PWMB")
    assert (group.dim.count, group.dim.increment) == (2, 0x100)
    assert len(compact(device.peripherals)) == 1


def test_a_template_kept_whole_has_a_dim_not_an_origin():
    device = Device(
        name="X",
        peripherals=[Peripheral("P", 0x0, registers=[Register("A[%s]", 0x0, dim=Dim(4, 4))])],
    )
    expand_dim(device)
    kept = device.peripherals[0].registers[0]
    assert kept.dim is not None and kept.dim.array
    assert kept.origin is None


def test_a_template_that_cannot_expand_has_no_origin():
    device = Device(
        name="X",
        peripherals=[Peripheral("P", 0x0, registers=[Register("R%s", 0x0, dim=Dim(2, None))])],
    )
    expand_dim(device)
    lone = device.peripherals[0].registers[0]
    assert lone.expanded_from == "R%s"
    assert lone.origin is None

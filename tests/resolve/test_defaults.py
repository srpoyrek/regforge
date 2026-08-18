"""Defaults resolution: size / access / reset inheritance down the chain."""

from regforge.ir import Access, Device, Field, Peripheral, Register
from regforge.readers.svd import SvdReader
from regforge.resolve import resolve_defaults


def _read_and_resolve(tmp_path, xml):
    svd = tmp_path / "d.svd"
    svd.write_text(xml, encoding="utf-8")
    device = SvdReader().read(svd)
    resolve_defaults(device)
    return device


def _register(device):
    return device.peripherals[0].registers[0]


def _field(device):
    return device.peripherals[0].registers[0].fields[0]


# --- size resolution (register -> device <size> -> device <width>) ---


def test_register_size_falls_back_to_bus_width(tmp_path):
    device = _read_and_resolve(
        tmp_path,
        "<device><name>X</name><width>16</width><peripherals><peripheral>"
        "<name>P</name><baseAddress>0x0</baseAddress><registers><register>"
        "<name>R</name><addressOffset>0x0</addressOffset></register>"
        "</registers></peripheral></peripherals></device>",
    )
    assert _register(device).size == 16


def test_register_size_resolution_order(tmp_path):
    device = _read_and_resolve(
        tmp_path,
        "<device><name>X</name><width>32</width><size>16</size><peripherals>"
        "<peripheral><name>P</name><baseAddress>0x0</baseAddress><registers>"
        "<register><name>R1</name><addressOffset>0x0</addressOffset></register>"
        "<register><name>R2</name><addressOffset>0x4</addressOffset><size>8</size></register>"
        "</registers></peripheral></peripherals></device>",
    )
    registers = device.peripherals[0].registers
    assert registers[0].size == 16  # inherits device <size>
    assert registers[1].size == 8  # own <size> wins


# --- access inheritance (device -> peripheral -> register -> field) ---


def _device_with_field(
    *, device_access=None, peripheral_access=None, register_access=None, field_access=None
):
    return Device(
        name="Chip",
        default_access=device_access,
        peripherals=[
            Peripheral(
                name="P",
                base_address=0,
                default_access=peripheral_access,
                registers=[
                    Register(
                        name="R",
                        address_offset=0,
                        size=32,
                        access=register_access,
                        fields=[Field("F", bit_offset=0, bit_width=1, access=field_access)],
                    )
                ],
            )
        ],
    )


def test_field_inherits_from_register():
    device = _device_with_field(register_access=Access.READ_ONLY)
    resolve_defaults(device)
    assert _register(device).access is Access.READ_ONLY
    assert _field(device).access is Access.READ_ONLY


def test_register_inherits_from_peripheral():
    device = _device_with_field(peripheral_access=Access.WRITE_ONLY)
    resolve_defaults(device)
    assert _register(device).access is Access.WRITE_ONLY
    assert _field(device).access is Access.WRITE_ONLY


def test_register_inherits_from_device():
    device = _device_with_field(device_access=Access.READ_ONLY)
    resolve_defaults(device)
    assert _register(device).access is Access.READ_ONLY


def test_own_field_access_beats_inheritance():
    device = _device_with_field(register_access=Access.READ_ONLY, field_access=Access.READ_WRITE)
    resolve_defaults(device)
    assert _field(device).access is Access.READ_WRITE


def test_access_absent_everywhere_defaults_read_write_and_warns():
    device = _device_with_field()  # nothing declares access at any level
    warnings = resolve_defaults(device)
    assert _register(device).access is Access.READ_WRITE
    assert _field(device).access is Access.READ_WRITE
    assert any("P.R" in w and "read-write" in w for w in warnings)


# --- reset value / mask inheritance ---


def test_reset_value_and_mask_inherit_from_device():
    device = Device(
        name="Chip",
        default_reset_value=0xABCD,
        default_reset_mask=0xFFFF,
        peripherals=[
            Peripheral(
                name="P",
                base_address=0,
                registers=[Register(name="R", address_offset=0, size=32)],
            )
        ],
    )
    resolve_defaults(device)
    register = _register(device)
    assert register.reset_value == 0xABCD
    assert register.reset_mask == 0xFFFF


def test_reset_value_absent_stays_none():
    device = Device(
        name="Chip",
        peripherals=[
            Peripheral(
                name="P",
                base_address=0,
                registers=[Register(name="R", address_offset=0, size=32)],
            )
        ],
    )
    resolve_defaults(device)
    assert _register(device).reset_value is None

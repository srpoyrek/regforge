"""Cross-checks over addressUnitBits / bus width / register sizes."""

from regforge.check import Severity, check_address_math
from regforge.ir import Device, Peripheral, Register


def _device(**kwargs):
    return Device(name="Chip", **kwargs)


def _with_register(**register_kwargs):
    return _device(
        address_unit_bits=8,
        bus_width=32,
        peripherals=[Peripheral(name="P", base_address=0, registers=[Register(**register_kwargs)])],
    )


def test_clean_device_has_no_findings(demo_device):
    assert check_address_math(demo_device) == []


def test_non_power_of_two_unit_bits_warns():
    # 24 is not a power of two -> typo signal. (bus_width 48 keeps it a multiple.)
    findings = check_address_math(_device(address_unit_bits=24, bus_width=48))
    assert any(f.severity is Severity.WARNING and "power of two" in f.message for f in findings)


def test_future_power_of_two_unit_bits_not_flagged():
    # 64/128 are exotic but valid widths; the check must NOT call them typos.
    for unit_bits in (64, 128):
        findings = check_address_math(_device(address_unit_bits=unit_bits, bus_width=unit_bits))
        assert not any("power of two" in f.message for f in findings)


def test_bus_narrower_than_unit_is_error():
    findings = check_address_math(_device(address_unit_bits=32, bus_width=16))
    assert any(f.severity is Severity.ERROR and "narrower" in f.message for f in findings)


def test_bus_not_multiple_of_unit_is_error():
    findings = check_address_math(_device(address_unit_bits=32, bus_width=48))
    assert any(f.severity is Severity.ERROR and "not a multiple" in f.message for f in findings)


def test_register_wider_than_bus_warns():
    findings = check_address_math(_with_register(name="R", address_offset=0, size=64))
    assert any(f.severity is Severity.WARNING and "> bus width" in f.message for f in findings)


def test_misaligned_offset_warns():
    # A 32-bit register (4 units at 8 bits/unit) at offset 0x2 is misaligned.
    findings = check_address_math(_with_register(name="R", address_offset=0x2, size=32))
    assert any("misaligned" in f.message for f in findings)

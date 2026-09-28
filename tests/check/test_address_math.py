"""Cross-checks over addressUnitBits / bus width / register sizes."""

from regforge.check import Severity, check_address_math
from regforge.ir import Cluster, Device, Dim, Field, Peripheral, Register


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


# --- arrays: a stride must at least cover one element ---


def _errors(findings):
    return [f.message for f in findings if f.severity is Severity.ERROR]


def test_array_stride_smaller_than_the_element_is_an_error():
    findings = check_address_math(
        _with_register(name="DATA", address_offset=0x10, size=32, dim=Dim(4, 2))
    )
    assert any("DATA[4]" in m and "overlap" in m for m in _errors(findings))


def test_packed_and_spaced_arrays_are_clean():
    for increment in (4, 8):
        findings = check_address_math(
            _with_register(name="DATA", address_offset=0x10, size=32, dim=Dim(4, increment))
        )
        assert not any("overlap" in f.message for f in findings)


def test_array_stride_check_waits_for_a_resolved_size():
    # No size yet (defaults not resolved): nothing to compare, nothing to report.
    findings = check_address_math(_with_register(name="DATA", address_offset=0x10, dim=Dim(4, 2)))
    assert findings == []


def test_field_array_increment_smaller_than_the_width_is_an_error():
    findings = check_address_math(
        _with_register(
            name="R", address_offset=0, size=32, fields=[Field("MODE", 0, 2, dim=Dim(16, 1))]
        )
    )
    assert any("P.R.MODE[16]" in m and "overlap" in m for m in _errors(findings))


def _dma(cluster: Cluster) -> Device:
    return _device(peripherals=[Peripheral(name="DMA", base_address=0, clusters=[cluster])])


def test_cluster_array_stride_smaller_than_its_contents_is_an_error():
    cluster = Cluster(
        "CH",
        0x10,
        dim=Dim(4, 0x4),
        registers=[Register("CTRL", 0x0, size=32), Register("SRC", 0x4, size=32)],
    )
    assert any(
        "DMA.CH[4]" in m and "overlap" in m for m in _errors(check_address_math(_dma(cluster)))
    )


def test_cluster_registers_are_checked_at_their_absolute_offset():
    # CTRL sits 0x2 into a cluster at 0x10: absolute 0x12, misaligned for 32 bits.
    cluster = Cluster("CH", 0x10, registers=[Register("CTRL", 0x2, size=32)])
    findings = check_address_math(_dma(cluster))
    assert any("DMA.CH.CTRL" in f.message and "misaligned" in f.message for f in findings)


def test_unpacked_array_warns_and_names_the_members():
    findings = check_address_math(
        _with_register(name="CH", address_offset=0x0, size=32, dim=Dim(4, 8, array=True))
    )
    warnings = [f.message for f in findings if f.severity is Severity.WARNING]
    assert any(
        "P.CH[4]: array stride 8" in m and "CH0..CH3" in m and "CH(ch_index)" in m for m in warnings
    )
    assert not _errors(findings)


def test_address_past_32_bits_is_an_error_naming_the_template():
    device = _device(
        peripherals=[
            Peripheral(
                name="HI3",
                base_address=0xFFFFF000,
                expanded_from="HI%s",
                registers=[Register("R", 0x1000, size=32)],  # ends at 0x1_0000_0004
            )
        ]
    )
    (message,) = _errors(check_address_math(device))
    assert "HI3: reaches 0x100000004, past the 32-bit address space" in message
    assert "(a copy expanded from HI%s)" in message


def test_fields_past_the_register_width_are_errors_collapsed_per_template():
    register = Register(
        "R",
        0,
        size=32,
        fields=[
            Field("F", 30, 4),  # a plain field: bits 30..33
            Field("A", 0, 4, dim=Dim(9, 4, array=True)),  # an array: 9 x 4 bits reach 36
            *[Field(f"M{i}", 4 * i, 4, expanded_from="M%s") for i in range(9)],  # M8 at 32..35
        ],
    )
    device = _device(peripherals=[Peripheral(name="P", base_address=0, registers=[register])])
    assert _errors(check_address_math(device)) == [
        "P.R.F: bits 30..33 run past the 32-bit register",
        "P.R.A[9]: bits 0..35 run past the 32-bit register",
        "P.R.M%s: M8..M8 (1 of its 9 copies) run past the 32-bit register",
    ]

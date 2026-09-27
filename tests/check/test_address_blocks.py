"""Linter: addressBlock consistency + cross-peripheral address overlap (B2)."""

from regforge.check import Severity, check_address_blocks, check_peripheral_overlap
from regforge.ir import AddressBlock, Cluster, Device, Dim, Peripheral, Register


def _device(*peripherals: Peripheral) -> Device:
    return Device(name="C", peripherals=list(peripherals))


def test_register_outside_its_block_warns():
    device = _device(
        Peripheral(
            name="P",
            base_address=0x0,
            registers=[Register("BIG", 0x40, size=32)],  # ends at 0x44, block is [0, 0x20)
            address_blocks=[AddressBlock(0, 0x20, "registers")],
        )
    )
    findings = check_address_blocks(device)
    assert len(findings) == 1
    assert findings[0].severity == Severity.WARNING
    assert "P.BIG" in findings[0].message and "outside" in findings[0].message


def test_register_within_block_is_clean():
    device = _device(
        Peripheral(
            name="P",
            base_address=0x0,
            registers=[Register("R", 0x1C, size=32)],  # ends at 0x20 == block end
            address_blocks=[AddressBlock(0, 0x20, "registers")],
        )
    )
    assert check_address_blocks(device) == []


def test_overlapping_blocks_within_one_peripheral_warn():
    device = _device(
        Peripheral(
            name="P",
            base_address=0x0,
            address_blocks=[
                AddressBlock(0x0, 0x20, "registers"),
                AddressBlock(0x10, 0x20, "buffer"),
            ],
        )
    )
    findings = check_address_blocks(device)
    assert len(findings) == 1
    assert "overlap" in findings[0].message


def test_cross_peripheral_overlap_errors():
    # UART block [0x40004000, 0x40004400) and TIMER starting at 0x40004200 overlap.
    device = _device(
        Peripheral(name="UART", base_address=0x40004000, address_blocks=[AddressBlock(0, 0x400)]),
        Peripheral(name="TIMER", base_address=0x40004200, address_blocks=[AddressBlock(0, 0x100)]),
    )
    findings = check_peripheral_overlap(device)
    assert len(findings) == 1
    assert findings[0].severity == Severity.ERROR
    assert "UART" in findings[0].message and "TIMER" in findings[0].message


def test_same_base_address_conflicts_without_blocks():
    # No addressBlocks: the register span defines the extent; same base -> overlap.
    device = _device(
        Peripheral(name="A", base_address=0x1000, registers=[Register("R", 0x0, size=32)]),
        Peripheral(name="B", base_address=0x1000, registers=[Register("R", 0x0, size=32)]),
    )
    findings = check_peripheral_overlap(device)
    assert len(findings) == 1
    assert findings[0].severity == Severity.ERROR


def test_spaced_peripherals_do_not_overlap():
    device = _device(
        Peripheral(name="A", base_address=0x1000, address_blocks=[AddressBlock(0, 0x100)]),
        Peripheral(name="B", base_address=0x1100, address_blocks=[AddressBlock(0, 0x100)]),
    )
    assert check_peripheral_overlap(device) == []


def test_fixture_has_no_address_block_findings(demo_device):
    assert check_address_blocks(demo_device) == []
    assert check_peripheral_overlap(demo_device) == []


# --- arrays and clusters are measured to their last element ---


def _array_in_block(count: int) -> Device:
    return _device(
        Peripheral(
            name="P",
            base_address=0x0,
            registers=[Register("DATA", 0x10, size=32, dim=Dim(count, 4))],
            address_blocks=[AddressBlock(0, 0x20, "registers")],
        )
    )


def test_array_running_past_its_block_warns():
    findings = check_address_blocks(_array_in_block(8))  # ends at 0x30, block is [0, 0x20)
    assert len(findings) == 1
    assert "P.DATA" in findings[0].message and "outside" in findings[0].message


def test_array_fitting_its_block_is_clean():
    assert check_address_blocks(_array_in_block(4)) == []  # ends at 0x20 == block end


def _channels() -> Cluster:
    return Cluster("CH", 0x10, dim=Dim(4, 0x10), registers=[Register("CTRL", 0x0, size=32)])


def test_cluster_array_running_past_its_block_warns():
    device = _device(
        Peripheral(
            name="DMA",
            base_address=0x0,
            clusters=[_channels()],  # last element ends at 0x44
            address_blocks=[AddressBlock(0, 0x40, "registers")],
        )
    )
    findings = check_address_blocks(device)
    assert len(findings) == 1 and "DMA.CH" in findings[0].message


def test_peripheral_overlap_uses_the_cluster_extent():
    # No blocks: DMA's span reaches its cluster array's last element, into TIMER.
    device = _device(
        Peripheral(name="DMA", base_address=0x1000, clusters=[_channels()]),
        Peripheral(name="TIMER", base_address=0x1040, registers=[Register("CR", 0x0, size=32)]),
    )
    assert len(check_peripheral_overlap(device)) == 1

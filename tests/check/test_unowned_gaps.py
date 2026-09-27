"""Linter: padding emitted over space no addressBlock claims."""

from regforge.check import Severity, check_unowned_gaps
from regforge.ir import AddressBlock, Cluster, Device, Dim, Peripheral, Register


def _device(*peripherals: Peripheral) -> Device:
    return Device(name="C", peripherals=list(peripherals))


def test_gap_inside_the_block_is_silent():
    # The block claims 0x0..0x400, so padding from 0x4 to 0x100 is space the
    # vendor said the peripheral owns -- truthful padding, nothing to report.
    device = _device(
        Peripheral(
            name="P",
            base_address=0x0,
            registers=[Register("A", 0x0, size=32), Register("B", 0x100, size=32)],
            address_blocks=[AddressBlock(0x0, 0x400, "registers")],
        )
    )
    assert check_unowned_gaps(device) == []


def test_gap_outside_every_block_warns_with_the_uncovered_count():
    # esp32's shape: the block stops at 0x100 but a register sits at 0x2000, so
    # 0x100..0x2000 is padded into the struct without ever being claimed.
    device = _device(
        Peripheral(
            name="FIFO",
            base_address=0x0,
            registers=[Register("CR", 0x0, size=32), Register("DATA", 0x2000, size=32)],
            address_blocks=[AddressBlock(0x0, 0x100, "registers")],
        )
    )
    findings = check_unowned_gaps(device)
    assert len(findings) == 1
    assert findings[0].severity is Severity.WARNING
    assert "7936 byte(s)" in findings[0].message  # 0x2000 - 0x100
    assert "[0x4, 0x2000)" in findings[0].message


def test_small_unowned_gap_is_tolerated():
    # A two-byte alignment hole is the median gap in real vendor files; naming
    # every one of them would bury the signal.
    device = _device(
        Peripheral(
            name="P",
            base_address=0x0,
            registers=[Register("A", 0x0, size=16), Register("B", 0x4, size=16)],
        )
    )
    assert check_unowned_gaps(device) == []


def test_several_blocks_cover_between_them():
    # Neither block spans the gap alone, but together they leave nothing
    # uncovered, so the padding is still declared space.
    device = _device(
        Peripheral(
            name="P",
            base_address=0x0,
            registers=[Register("A", 0x0, size=32), Register("B", 0x40, size=32)],
            address_blocks=[
                AddressBlock(0x0, 0x20, "registers"),
                AddressBlock(0x20, 0x40, "buffer"),
            ],
        )
    )
    assert check_unowned_gaps(device) == []


def _dma(block_size: int) -> Device:
    return _device(
        Peripheral(
            name="DMA",
            base_address=0x0,
            registers=[Register("CFG", 0x0, size=32)],
            clusters=[
                Cluster("CH", 0x100, dim=Dim(2, 0x10), registers=[Register("CTRL", 0x0, size=32)])
            ],
            address_blocks=[AddressBlock(0x0, block_size, "registers")],
        )
    )


def test_gap_before_a_cluster_array_inside_the_block_is_silent():
    assert check_unowned_gaps(_dma(0x400)) == []


def test_gap_before_a_cluster_array_outside_the_block_warns():
    findings = check_unowned_gaps(_dma(0x4))  # the block stops where CFG ends
    assert len(findings) == 1
    assert "DMA" in findings[0].message and "252 byte(s)" in findings[0].message

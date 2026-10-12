"""DeviceFacts: the widths a device's page is laid out by, worked out once."""

from regforge.ir import AddressBlock, Cluster, Device, Peripheral, Register
from regforge.writers.html.device.device_facts import DeviceFacts


def test_the_bus_width_is_the_devices():
    assert DeviceFacts.of(Device(name="D", bus_width=16)).bus_width == 16


def test_an_address_has_as_many_digits_as_the_bus_is_wide():
    assert DeviceFacts.of(Device(name="D", bus_width=32)).address_digits == 8
    assert DeviceFacts.of(Device(name="D", bus_width=16)).address_digits == 4
    assert DeviceFacts.of(Device(name="D", bus_width=64)).address_digits == 16


def test_an_offset_has_as_many_digits_as_the_largest_register_offset_needs():
    device = Device(
        name="D",
        peripherals=[
            Peripheral("A", 0x0, registers=[Register("R", 0xFC, size=32)]),
            Peripheral("B", 0x1000, registers=[Register("R", 0x1FC, size=32)]),
        ],
    )
    assert DeviceFacts.of(device).offset_digits == 3


def test_a_register_inside_a_cluster_counts_from_the_peripheral():
    cluster = Cluster("CH", 0x1000, registers=[Register("CTRL", 0x4, size=32)])
    device = Device(name="D", peripherals=[Peripheral("DMA", 0x0, clusters=[cluster])])
    assert DeviceFacts.of(device).offset_digits == 4


def test_an_address_block_counts_by_its_offset_and_its_size():
    device = Device(
        name="D",
        peripherals=[Peripheral("A", 0x0, address_blocks=[AddressBlock(0x0, 0x10000)])],
    )
    assert DeviceFacts.of(device).offset_digits == 5


def test_a_device_with_nothing_to_place_needs_no_offset_digits():
    assert DeviceFacts.of(Device(name="D")).offset_digits == 0

"""PeripheralHtml: the block of one peripheral and everything it holds."""

from regforge.ir import AddressBlock, Cluster, Dim, Interrupt, Peripheral, Register
from regforge.writers.html.context import RenderContext
from regforge.writers.html.device.device_facts import DeviceFacts
from regforge.writers.html.device.peripheral.peripheral import PeripheralHtml

FACTS = DeviceFacts(bus_width=32, address_digits=8, offset_digits=4)


def _renderer():
    return PeripheralHtml(RenderContext.default())


def _uart():
    return Peripheral(
        "UART1",
        0x40005000,
        description="Serial port",
        derived_from="UART0",
        group_name="UART",
        registers=[Register("DR", 0x4, size=32)],
        interrupts=[Interrupt("U1", 21)],
        address_blocks=[AddressBlock(0x0, 0x20, "registers")],
    )


def test_it_shows_the_peripherals_facts():
    html = _renderer().render(_uart(), FACTS)
    assert 'id="UART1"' in html and "0x40005000" in html and "Serial port" in html
    assert "Group <b>UART</b>" in html


def test_it_links_to_the_peripheral_it_is_derived_from():
    assert 'href="#UART0"' in _renderer().render(_uart(), FACTS)


def test_it_lists_address_blocks_and_interrupts():
    html = _renderer().render(_uart(), FACTS)
    assert "<h3>Address blocks</h3>" in html and "0x0020" in html
    assert "<h3>Interrupts</h3>" in html and "<td>U1</td>" in html


def test_it_has_a_register_table_and_a_block_for_each_register():
    html = _renderer().render(_uart(), FACTS)
    assert "<h3>Registers</h3>" in html
    assert 'href="#UART1.DR"' in html and 'id="UART1.DR"' in html


def test_a_register_in_a_cluster_is_named_by_its_path():
    cluster = Cluster("CH", 0x10, registers=[Register("CTRL", 0x0)], dim=Dim(4, 0x10, array=True))
    html = _renderer().render(Peripheral("DMA", 0x0, clusters=[cluster]), FACTS)
    assert 'id="DMA.CH.CTRL"' in html and "array of 4, 0x10 units apart" in html


def test_a_peripheral_with_nothing_to_list_leaves_those_parts_out():
    html = _renderer().render(Peripheral("P", 0x0), FACTS)
    assert "Address blocks" not in html and "Interrupts" not in html and "<h3>Registers" not in html


def test_the_row_links_to_the_section_and_names_the_interrupts():
    row = _renderer().row(_uart(), FACTS)
    assert 'href="#UART1"' in row and "U1" in row and "0x40005000" in row


def test_the_base_address_uses_the_devices_address_digits():
    short_bus = DeviceFacts(bus_width=16, address_digits=4, offset_digits=2)
    peripheral = Peripheral("P", 0x10)
    assert "0x0010" in _renderer().render(peripheral, short_bus)
    assert "0x0010" in _renderer().row(peripheral, short_bus)

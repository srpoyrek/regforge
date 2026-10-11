"""AddressBlockHtml: the block of one address block."""

from regforge.ir import AddressBlock
from regforge.writers.html.address_block import AddressBlockHtml
from regforge.writers.html.context import RenderContext
from regforge.writers.html.device_facts import DeviceFacts

FACTS = DeviceFacts(bus_width=32, address_digits=8, offset_digits=4)


def test_it_shows_offset_size_and_usage():
    html = AddressBlockHtml(RenderContext.default()).render(
        AddressBlock(0x10, 0x20, "buffer"), FACTS
    )
    assert "0x0010" in html and "0x0020" in html and "buffer" in html


def test_a_block_with_no_usage_holds_registers():
    html = AddressBlockHtml(RenderContext.default()).render(AddressBlock(0x0, 0x8), FACTS)
    assert "registers" in html


def test_the_offset_and_size_use_the_devices_offset_digits():
    narrow = DeviceFacts(bus_width=32, address_digits=8, offset_digits=2)
    html = AddressBlockHtml(RenderContext.default()).render(AddressBlock(0x10, 0x20), narrow)
    assert "0x10" in html and "0x20" in html and "0x0010" not in html

"""AddressBlockHtml: the block of one address block."""

from regforge.ir import AddressBlock
from regforge.writers.html.address_block import AddressBlockHtml
from regforge.writers.html.context import RenderContext


def test_it_shows_offset_size_and_usage():
    html = AddressBlockHtml(RenderContext.default()).render(AddressBlock(0x10, 0x20, "buffer"))
    assert "0x0010" in html and "0x0020" in html and "buffer" in html


def test_a_block_with_no_usage_holds_registers():
    html = AddressBlockHtml(RenderContext.default()).render(AddressBlock(0x0, 0x8))
    assert "registers" in html

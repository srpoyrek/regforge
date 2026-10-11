"""The HTML block of one address block."""

from __future__ import annotations

from markupsafe import Markup

from regforge.ir import AddressBlock
from regforge.writers.html.context import ElementHtml
from regforge.writers.html.wording import hex_


class AddressBlockHtml(ElementHtml):
    """Renders one :class:`~regforge.ir.AddressBlock` as a table row."""

    def render(self, block: AddressBlock) -> Markup:
        """The block's offset, size and usage."""
        return self._fill(
            "address_block.html.j2",
            offset=hex_(block.offset, 4),
            size=hex_(block.size, 4),
            usage=block.usage or "registers",
        )

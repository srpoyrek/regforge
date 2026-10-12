"""The HTML wording of a data type."""

from __future__ import annotations

from regforge.ir import DataType
from regforge.writers.html.context import LeafHtml


class DataTypeHtml(LeafHtml):
    """Renders a :class:`~regforge.ir.DataType` as the C type the register is read as."""

    def label(self, data_type: DataType | None) -> str | None:
        """The type as the schema spells it, ``int32_t``; ``None`` when the register states none."""
        return None if data_type is None else data_type.value

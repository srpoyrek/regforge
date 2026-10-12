"""Reads a ``<field>`` element."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from regforge.ir import Field
from regforge.readers.svd.device.access import AccessParser
from regforge.readers.svd.device.peripheral.dim import DimParser
from regforge.readers.svd.device.peripheral.register.field.enum_set.enum_set import EnumSetParser
from regforge.readers.svd.device.peripheral.register.modified_write_values import (
    ModifiedWriteValuesParser,
)
from regforge.readers.svd.device.peripheral.register.read_action import ReadActionParser
from regforge.readers.svd.device.peripheral.register.write_constraint import WriteConstraintParser
from regforge.readers.svd.element_parser import ElementParser, ParseContext
from regforge.readers.svd.primitives import child_int, child_text


class FieldParser(ElementParser):
    """Reads one ``<field>`` as a :class:`~regforge.ir.Field`."""

    def __init__(self, context: ParseContext) -> None:
        super().__init__(context)
        self._access = AccessParser(context)
        self._dim = DimParser(context)
        self._enum_set = EnumSetParser(context)
        self._modified_write_values = ModifiedWriteValuesParser(context)
        self._read_action = ReadActionParser(context)
        self._write_constraint = WriteConstraintParser()

    def bits(self, element: ET.Element) -> tuple[int, int]:
        """Return ``(bit_offset, bit_width)`` from any SVD bit-range encoding."""
        bit_range = child_text(element, "bitRange")
        if bit_range is not None:  # form: "[msb:lsb]"
            msb_text, lsb_text = bit_range.strip().lstrip("[").rstrip("]").split(":")
            msb, lsb = int(msb_text), int(lsb_text)
            return lsb, msb - lsb + 1

        offset = child_int(element, "bitOffset")
        width = child_int(element, "bitWidth")
        if offset is not None and width is not None:
            return offset, width

        lsb = child_int(element, "lsb")
        msb = child_int(element, "msb")
        if lsb is not None and msb is not None:
            return lsb, msb - lsb + 1

        name = child_text(element, "name") or "<unnamed>"
        raise ValueError(f"field {name!r} has no recognizable bit-range specification")

    def parse(self, element: ET.Element) -> Field:
        """The field ``element`` describes."""
        name = child_text(element, "name") or ""
        offset, width = self.bits(element)
        enum_sets = [self._enum_set.parse(e) for e in element.findall("enumeratedValues")]
        return Field(
            name=name,
            bit_offset=offset,
            bit_width=width,
            description=child_text(element, "description"),
            access=self._access.parse(element),
            enum_sets=enum_sets,
            dim=self._dim.parse(element, name),
            modified_write_values=self._modified_write_values.parse(element),
            read_action=self._read_action.parse(element),
            write_constraint=self._write_constraint.parse(element),
        )

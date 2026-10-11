"""Reads a ``<register>`` element."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from regforge.ir import Register
from regforge.readers.svd.access import AccessParser
from regforge.readers.svd.data_type import DataTypeParser
from regforge.readers.svd.dim import DimParser
from regforge.readers.svd.element_parser import ElementParser, ParseContext
from regforge.readers.svd.field import FieldParser
from regforge.readers.svd.modified_write_values import ModifiedWriteValuesParser
from regforge.readers.svd.primitives import child_int, child_text
from regforge.readers.svd.protection import ProtectionParser
from regforge.readers.svd.read_action import ReadActionParser
from regforge.readers.svd.write_constraint import WriteConstraintParser


class RegisterParser(ElementParser):
    """Reads one ``<register>`` as a :class:`~regforge.ir.Register`."""

    def __init__(self, context: ParseContext) -> None:
        super().__init__(context)
        self._access = AccessParser()
        self._data_type = DataTypeParser()
        self._dim = DimParser(context)
        self._field = FieldParser(context)
        self._modified_write_values = ModifiedWriteValuesParser()
        self._protection = ProtectionParser()
        self._read_action = ReadActionParser()
        self._write_constraint = WriteConstraintParser()

    def parse(self, element: ET.Element) -> Register:
        """The register ``element`` describes.

        Register-property values are stored raw (``None`` when silent); the defaults
        resolution pass fills them from the inheritance chain.
        """
        name = child_text(element, "name") or ""
        alternate = child_text(element, "alternateRegister")
        group = child_text(element, "alternateGroup")
        if group:
            # <alternateGroup>: the same register name reused in another group is
            # the spec's other spelling of an alternate view. Spelled NAME_GROUP so
            # it is an identifier, and linked to the plainly named register.
            alternate = alternate or name
            name = f"{name}_{group}"
        return Register(
            name=name,
            derived_from=element.get("derivedFrom"),  # XML attribute, as on a peripheral
            alternate_register=alternate,
            address_offset=child_int(element, "addressOffset", 0),
            size=child_int(element, "size"),
            reset_value=child_int(element, "resetValue"),
            reset_mask=child_int(element, "resetMask"),
            description=child_text(element, "description"),
            access=self._access.parse(element),
            fields=[self._field.parse(f) for f in element.findall("./fields/field")],
            dim=self._dim.parse(element, name),
            display_name=child_text(element, "displayName"),
            data_type=self._data_type.parse(element),
            protection=self._protection.parse(element),
            modified_write_values=self._modified_write_values.parse(element),
            read_action=self._read_action.parse(element),
            write_constraint=self._write_constraint.parse(element),
        )

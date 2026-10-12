"""Reads a ``<register>`` element."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from regforge.ir import AlternateSet, Register
from regforge.readers.svd.device.access import AccessParser
from regforge.readers.svd.device.peripheral.dim import DimParser
from regforge.readers.svd.device.peripheral.register.data_type import DataTypeParser
from regforge.readers.svd.device.peripheral.register.field.field import FieldParser
from regforge.readers.svd.device.peripheral.register.modified_write_values import (
    ModifiedWriteValuesParser,
)
from regforge.readers.svd.device.peripheral.register.read_action import ReadActionParser
from regforge.readers.svd.device.peripheral.register.write_constraint import WriteConstraintParser
from regforge.readers.svd.device.protection import ProtectionParser
from regforge.readers.svd.element_parser import ElementParser, ParseContext
from regforge.readers.svd.primitives import child_int, child_text


class RegisterParser(ElementParser):
    """Reads one ``<register>`` as a :class:`~regforge.ir.Register`."""

    def __init__(self, context: ParseContext) -> None:
        super().__init__(context)
        self._access = AccessParser(context)
        self._data_type = DataTypeParser(context)
        self._dim = DimParser(context)
        self._field = FieldParser(context)
        self._modified_write_values = ModifiedWriteValuesParser(context)
        self._protection = ProtectionParser(context)
        self._read_action = ReadActionParser(context)
        self._write_constraint = WriteConstraintParser()

    def parse(self, element: ET.Element) -> Register:
        """The register ``element`` describes.

        Register-property values are stored raw (``None`` when silent); the defaults
        resolution pass fills them from the inheritance chain.
        """
        name = child_text(element, "name") or ""
        return Register(
            name=name,
            derived_from=element.get("derivedFrom"),  # XML attribute, as on a peripheral
            alternate_group=child_text(element, "alternateGroup"),
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

    def parse_set(self, element: ET.Element) -> AlternateSet:
        """The register ``element`` describes, as the set of one view it starts out as.

        The set carries what the file declared about it: ``<alternateRegister>`` is kept as
        written in ``joins``, for ``resolve_alternates`` to merge once every name is final.
        """
        return AlternateSet((self.parse(element),), joins=child_text(element, "alternateRegister"))

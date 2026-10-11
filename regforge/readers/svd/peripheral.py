"""Reads a ``<peripheral>`` element."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from regforge.ir import Peripheral
from regforge.readers.svd.access import AccessParser
from regforge.readers.svd.address_block import AddressBlockParser
from regforge.readers.svd.cluster import ClusterParser
from regforge.readers.svd.dim import DimParser
from regforge.readers.svd.element_parser import ElementParser, ParseContext
from regforge.readers.svd.interrupt import InterruptParser
from regforge.readers.svd.primitives import child_int, child_text
from regforge.readers.svd.protection import ProtectionParser
from regforge.readers.svd.register import RegisterParser


class PeripheralParser(ElementParser):
    """Reads one ``<peripheral>`` as a :class:`~regforge.ir.Peripheral`."""

    def __init__(self, context: ParseContext) -> None:
        super().__init__(context)
        self._access = AccessParser()
        self._address_block = AddressBlockParser()
        self._cluster = ClusterParser(context)
        self._dim = DimParser(context)
        self._interrupt = InterruptParser()
        self._protection = ProtectionParser()
        self._register = RegisterParser(context)

    def parse(self, element: ET.Element) -> Peripheral:
        """The peripheral ``element`` describes."""
        name = child_text(element, "name") or ""
        return Peripheral(
            name=name,
            base_address=child_int(element, "baseAddress", 0),
            description=child_text(element, "description"),
            derived_from=element.get("derivedFrom"),  # XML attribute, not a child
            group_name=child_text(element, "groupName"),
            header_struct_name=child_text(element, "headerStructName"),
            default_size=child_int(element, "size"),
            default_access=self._access.parse(element),
            default_reset_value=child_int(element, "resetValue"),
            default_reset_mask=child_int(element, "resetMask"),
            default_protection=self._protection.parse(element),
            alternate_sets=[
                self._register.parse_set(r) for r in element.findall("./registers/register")
            ],
            interrupts=[self._interrupt.parse(i) for i in element.findall("./interrupt")],
            address_blocks=[
                self._address_block.parse(b) for b in element.findall("./addressBlock")
            ],
            clusters=[self._cluster.parse(c) for c in element.findall("./registers/cluster")],
            dim=self._dim.parse(element, name, element.get("derivedFrom") is not None),
        )

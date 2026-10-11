"""Reads a ``<cluster>`` element."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from regforge.ir import Cluster
from regforge.readers.svd.access import AccessParser
from regforge.readers.svd.dim import DimParser
from regforge.readers.svd.element_parser import ElementParser, ParseContext
from regforge.readers.svd.primitives import child_int, child_text
from regforge.readers.svd.protection import ProtectionParser
from regforge.readers.svd.register import RegisterParser


class ClusterParser(ElementParser):
    """Reads one ``<cluster>`` as a :class:`~regforge.ir.Cluster`, nested clusters included."""

    def __init__(self, context: ParseContext) -> None:
        super().__init__(context)
        self._access = AccessParser()
        self._dim = DimParser(context)
        self._protection = ProtectionParser()
        self._register = RegisterParser(context)

    def parse(self, element: ET.Element) -> Cluster:
        """The cluster ``element`` describes.

        Inside a cluster, registers and nested clusters are direct children: the
        schema has no ``<registers>`` wrapper at this level.
        """
        name = child_text(element, "name") or ""
        return Cluster(
            name=name,
            address_offset=child_int(element, "addressOffset", 0),
            description=child_text(element, "description"),
            header_struct_name=child_text(element, "headerStructName"),
            derived_from=element.get("derivedFrom"),  # XML attribute, as on a peripheral
            default_size=child_int(element, "size"),
            default_access=self._access.parse(element),
            default_reset_value=child_int(element, "resetValue"),
            default_reset_mask=child_int(element, "resetMask"),
            default_protection=self._protection.parse(element),
            alternate_sets=[self._register.parse_set(r) for r in element.findall("./register")],
            clusters=[self.parse(c) for c in element.findall("./cluster")],
            dim=self._dim.parse(element, name, element.get("derivedFrom") is not None),
        )

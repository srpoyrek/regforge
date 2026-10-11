"""The SVD reader: opens a file and hands its root to the device parser."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from regforge.ir import Device
from regforge.readers.base import Reader, Source
from regforge.readers.svd.device import DeviceParser
from regforge.readers.svd.element_parser import ParseContext


class SvdReader(Reader):
    """Reader for CMSIS-SVD (``.svd``) device description files."""

    format_name = "svd"
    file_extensions = (".svd",)

    def read(self, source: Source) -> Device:
        """Parse the SVD file at ``source`` into a :class:`~regforge.ir.Device`.

        Register-property defaults are stored raw at each level; run
        :func:`regforge.resolve.resolve_defaults` to fill them in. Anything the
        reader had to normalise on the way is left in :attr:`warnings`.
        """
        root = ET.parse(str(source)).getroot()
        self.warnings = []
        return DeviceParser(ParseContext(self.warnings)).parse(root)

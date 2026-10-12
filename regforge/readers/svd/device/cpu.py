"""Reads the ``<cpu>`` element."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from regforge.ir import Cpu
from regforge.readers.svd.primitives import child_bool, child_int, child_text


class CpuParser:
    """Reads the ``<cpu>`` block as a :class:`~regforge.ir.Cpu`."""

    def parse(self, element: ET.Element) -> Cpu:
        """The core ``element`` describes."""
        return Cpu(
            name=child_text(element, "name"),
            revision=child_text(element, "revision"),
            endian=child_text(element, "endian"),
            mpu_present=child_bool(element, "mpuPresent"),
            fpu_present=child_bool(element, "fpuPresent"),
            vtor_present=child_bool(element, "vtorPresent"),
            nvic_prio_bits=child_int(element, "nvicPrioBits"),
            vendor_systick=child_bool(element, "vendorSystickConfig"),
            num_interrupts=child_int(element, "deviceNumInterrupts"),
        )

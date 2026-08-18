"""CMSIS-SVD reader.

Parses a System View Description (SVD) file into the regforge intermediate
representation using only the Python standard library. The reader covers the
core SVD hierarchy -- peripherals, registers, fields, and enumerated values --
and accepts all three field bit-range encodings: ``bitOffset``/``bitWidth``,
``bitRange``, and ``lsb``/``msb``.

Notes:
    Peripheral and register inheritance (``derivedFrom``), register clusters,
    and dimensioned arrays (``dim``) are not expanded by this reader.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from ..ir import Cpu, Device, EnumeratedValue, Field, Peripheral, Register
from .base import Reader, Source


def parse_svd_int(text: str) -> int:
    """Parse an SVD integer literal.

    Supports hexadecimal (``0x1F``), binary (``0b1010`` or ``#1010``), and
    decimal (``42``) notations as defined by the SVD schema.
    """
    token = text.strip().lower()
    if token.startswith("0x"):
        return int(token, 16)
    if token.startswith("0b"):
        return int(token[2:], 2)
    if token.startswith("#"):
        return int(token[1:], 2)
    return int(token, 10)


def parse_svd_bool(text: str) -> bool | None:
    """Parse an SVD boolean, accepting both ``true``/``false`` and ``1``/``0``.

    Some vendor files (Nordic, for example) write booleans as ``1``/``0``
    rather than ``true``/``false``; both spellings are normalized here.
    Anything unrecognized returns ``None`` so callers can treat it as absent.
    """
    token = text.strip().lower()
    if token in ("true", "1"):
        return True
    if token in ("false", "0"):
        return False
    return None


def _text(element: ET.Element, tag: str) -> str | None:
    """Return the stripped text of ``element``'s ``tag`` child, or ``None``."""
    child = element.find(tag)
    if child is not None and child.text is not None:
        return child.text.strip()
    return None


def _int(element: ET.Element, tag: str, default: int | None = None) -> int | None:
    """Return the integer value of ``element``'s ``tag`` child, or ``default``."""
    raw = _text(element, tag)
    return parse_svd_int(raw) if raw is not None else default


def _bool(element: ET.Element, tag: str) -> bool | None:
    """Return the boolean value of ``element``'s ``tag`` child, or ``None``."""
    raw = _text(element, tag)
    return parse_svd_bool(raw) if raw is not None else None


def _parse_bits(field_element: ET.Element) -> tuple[int, int]:
    """Return ``(bit_offset, bit_width)`` from any SVD bit-range encoding."""
    bit_range = _text(field_element, "bitRange")
    if bit_range is not None:  # form: "[msb:lsb]"
        msb_text, lsb_text = bit_range.strip().lstrip("[").rstrip("]").split(":")
        msb, lsb = int(msb_text), int(lsb_text)
        return lsb, msb - lsb + 1

    offset = _int(field_element, "bitOffset")
    width = _int(field_element, "bitWidth")
    if offset is not None and width is not None:
        return offset, width

    lsb = _int(field_element, "lsb")
    msb = _int(field_element, "msb")
    if lsb is not None and msb is not None:
        return lsb, msb - lsb + 1

    name = _text(field_element, "name") or "<unnamed>"
    raise ValueError(f"field {name!r} has no recognizable bit-range specification")


def _build_field(field_element: ET.Element) -> Field:
    offset, width = _parse_bits(field_element)
    enums = [
        EnumeratedValue(
            name=_text(value_element, "name") or "",
            value=parse_svd_int(_text(value_element, "value") or "0"),
            description=_text(value_element, "description"),
        )
        for value_element in field_element.findall("./enumeratedValues/enumeratedValue")
        if _text(value_element, "value") is not None
    ]
    return Field(
        name=_text(field_element, "name") or "",
        bit_offset=offset,
        bit_width=width,
        description=_text(field_element, "description"),
        access=_text(field_element, "access"),
        enums=enums,
    )


def _build_register(register_element: ET.Element) -> Register:
    return Register(
        name=_text(register_element, "name") or "",
        address_offset=_int(register_element, "addressOffset", 0) or 0,
        size=_int(register_element, "size", 32) or 32,
        reset_value=_int(register_element, "resetValue", 0) or 0,
        description=_text(register_element, "description"),
        access=_text(register_element, "access"),
        fields=[_build_field(f) for f in register_element.findall("./fields/field")],
    )


def _build_cpu(cpu_element: ET.Element) -> Cpu:
    return Cpu(
        name=_text(cpu_element, "name"),
        revision=_text(cpu_element, "revision"),
        endian=_text(cpu_element, "endian"),
        mpu_present=_bool(cpu_element, "mpuPresent"),
        fpu_present=_bool(cpu_element, "fpuPresent"),
        vtor_present=_bool(cpu_element, "vtorPresent"),
        nvic_prio_bits=_int(cpu_element, "nvicPrioBits"),
        vendor_systick=_bool(cpu_element, "vendorSystickConfig"),
        num_interrupts=_int(cpu_element, "deviceNumInterrupts"),
    )


def _build_peripheral(peripheral_element: ET.Element) -> Peripheral:
    return Peripheral(
        name=_text(peripheral_element, "name") or "",
        base_address=_int(peripheral_element, "baseAddress", 0) or 0,
        description=_text(peripheral_element, "description"),
        registers=[_build_register(r) for r in peripheral_element.findall("./registers/register")],
    )


class SvdReader(Reader):
    """Reader for CMSIS-SVD (``.svd``) device description files."""

    format_name = "svd"
    file_extensions = (".svd",)

    def read(self, source: Source) -> Device:
        """Parse the SVD file at ``source`` into a :class:`~regforge.ir.Device`."""
        root = ET.parse(str(source)).getroot()
        cpu_element = root.find("cpu")
        return Device(
            name=_text(root, "name") or "device",
            description=_text(root, "description"),
            vendor=_text(root, "vendor"),
            series=_text(root, "series"),
            version=_text(root, "version"),
            license_text=_text(root, "licenseText"),
            cpu=_build_cpu(cpu_element) if cpu_element is not None else None,
            peripherals=[_build_peripheral(p) for p in root.findall("./peripherals/peripheral")],
        )

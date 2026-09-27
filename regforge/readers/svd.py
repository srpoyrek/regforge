"""CMSIS-SVD reader.

Parses a System View Description (SVD) file into the regforge intermediate
representation using only the Python standard library. The reader covers the
core SVD hierarchy -- peripherals, registers, fields, and enumerated values --
and accepts all three field bit-range encodings: ``bitOffset``/``bitWidth``,
``bitRange``, and ``lsb``/``msb``.

Notes:
    Inheritance (``derivedFrom``) and arrays (``dim``) are parsed, not
    expanded, by this reader: :mod:`regforge.resolve` does both. Clusters are
    walked, registers and nested clusters alike.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from enum import IntEnum
from typing import overload

from ..ir import (
    DEFAULT_ADDRESS_UNIT_BITS,
    DEFAULT_BUS_WIDTH,
    Access,
    AddressBlock,
    Cluster,
    Cpu,
    Device,
    Dim,
    EnumeratedValue,
    Field,
    Interrupt,
    Peripheral,
    Register,
)
from .base import Reader, Source


class Radix(IntEnum):
    """Numeric bases accepted for SVD integer literals."""

    HEX = 16
    BINARY = 2
    DECIMAL = 10


def parse_svd_int(text: str) -> int:
    """Parse an SVD integer literal.

    Supports hexadecimal (``0x1F``), binary (``0b1010`` or ``#1010``), and
    decimal (``42``) notations as defined by the SVD schema.
    """
    token = text.strip().lower()
    if token.startswith("0x"):
        return int(token, Radix.HEX)
    if token.startswith("0b"):
        return int(token, Radix.BINARY)
    if token.startswith("#"):
        return int(token.removeprefix("#"), Radix.BINARY)
    return int(token, Radix.DECIMAL)


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


@overload
def _int(element: ET.Element, tag: str) -> int | None: ...
@overload
def _int(element: ET.Element, tag: str, default: int) -> int: ...
def _int(element: ET.Element, tag: str, default: int | None = None) -> int | None:
    """Return the integer value of ``element``'s ``tag`` child, or ``default``.

    Overloaded so a caller that passes an ``int`` default gets ``int`` back (not
    ``int | None``) -- so the parsed value can flow straight into an ``int`` field.
    """
    raw = _text(element, tag)
    return parse_svd_int(raw) if raw is not None else default


def _bool(element: ET.Element, tag: str) -> bool | None:
    """Return the boolean value of ``element``'s ``tag`` child, or ``None``."""
    raw = _text(element, tag)
    return parse_svd_bool(raw) if raw is not None else None


def _access(element: ET.Element, tag: str = "access") -> Access | None:
    """Return the :class:`~regforge.ir.Access` of ``element``'s ``tag`` child.

    Returns ``None`` when the element is absent or holds an unrecognized value
    (so the defaults resolution pass fills it from a higher level).
    """
    raw = _text(element, tag)
    if raw is None:
        return None
    try:
        return Access(raw)
    except ValueError:
        return None


_RANGE = re.compile(r"(\d+)-(\d+)|([A-Za-z])-([A-Za-z])")


def parse_dim_index(text: str, warnings: list[str] | None = None) -> list[str]:
    """Parse an SVD ``<dimIndex>`` into the labels that replace ``%s``.

    A comma-separated list of labels, any of which may be a numeric range
    (``0-3``) or a single-letter range (``A-D``); ``0-3,7`` mixes the forms.
    Whitespace around a label is dropped and both ends of a range are kept. A
    reversed range (``3-0``) is read ascending and noted in ``warnings``.
    """
    labels: list[str] = []
    for part in text.split(","):
        part = part.strip()
        match = _RANGE.fullmatch(part)
        if match is None:
            labels.append(part)
            continue
        if match.group(1) is not None:
            first, last = int(match.group(1)), int(match.group(2))
            if first > last:
                if warnings is not None:
                    warnings.append(f"dimIndex range {part} is reversed -- read as {last}-{first}")
                first, last = last, first
            labels += [str(i) for i in range(first, last + 1)]
        else:
            first, last = match.group(3), match.group(4)
            if first > last:
                if warnings is not None:
                    warnings.append(f"dimIndex range {part} is reversed -- read as {last}-{first}")
                first, last = last, first
            labels += [chr(code) for code in range(ord(first), ord(last) + 1)]
    return labels


def _dim(element: ET.Element, name: str, warnings: list[str], derived: bool = False) -> Dim | None:
    """Return the ``<dim>`` group of ``element``, or ``None`` when it has none.

    Only ``%s`` with no ``<dim>``, and a negative ``<dim>``, are refused here,
    like a field with no bit range. A ``<dim>`` of 0, or one with no
    ``<dimIncrement>``, is stored as read: expansion reports it and drops the
    element or keeps one instance. A ``<dimIncrement>`` with no ``<dim>`` is
    noted and ignored -- unless the element carries ``derivedFrom``, in which
    case a ``%s`` name, ``<dimIncrement>``, ``<dimIndex>`` or ``<dimName>`` with no
    ``<dim>`` is a partial ``Dim`` that expansion completes from the base
    template (``derived``). Labels are only parsed here; how
    many there are and whether they are usable names is judged by expansion,
    which can report at the element's path. The stride is not looked at: it
    needs the resolved register size, which exists only after defaults.
    """
    count = _int(element, "dim")
    if count is None:
        written = ("dimIncrement", "dimIndex", "dimName")
        if "%s" not in name and all(_text(element, tag) is None for tag in written):
            return None
        if not derived:
            if _text(element, "dimIncrement") is not None:
                warnings.append(f"{name}: <dimIncrement> without <dim> -- ignored")
            if "%s" in name:
                raise ValueError(f"{name!r} has a %s placeholder but no <dim>")
            return None
        # A derived element inherits what it leaves unsaid; the count comes
        # from the base template, in expansion's pre-pass.
    if count is not None and count < 0:
        raise ValueError(f"{name!r}: <dim> cannot be negative, got {count}")
    # A missing <dimIncrement> stays None: expansion reports it and keeps one
    # instance, since the copies' addresses are unknown.
    increment = _int(element, "dimIncrement")
    index_text = _text(element, "dimIndex")
    index = None
    if index_text is not None:
        notes: list[str] = []
        index = parse_dim_index(index_text, notes)
        warnings += [f"{name}: {note}" for note in notes]
    array_index = [
        EnumeratedValue(
            name=_text(value_element, "name") or "",
            value=parse_svd_int(_text(value_element, "value") or "0"),
            description=_text(value_element, "description"),
        )
        for value_element in element.findall("./dimArrayIndex/enumeratedValue")
        if _text(value_element, "value") is not None
    ]
    return Dim(
        count=count,
        increment=increment,
        index=index,
        name=_text(element, "dimName"),
        array_index=array_index,
    )


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


def _build_field(field_element: ET.Element, warnings: list[str]) -> Field:
    name = _text(field_element, "name") or ""
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
        name=name,
        bit_offset=offset,
        bit_width=width,
        description=_text(field_element, "description"),
        access=_access(field_element),
        enums=enums,
        dim=_dim(field_element, name, warnings),
    )


def _build_register(register_element: ET.Element, warnings: list[str]) -> Register:
    # Register-property values are stored raw (None when silent); the defaults
    # resolution pass fills them from the inheritance chain.
    name = _text(register_element, "name") or ""
    return Register(
        name=name,
        address_offset=_int(register_element, "addressOffset", 0),
        size=_int(register_element, "size"),
        reset_value=_int(register_element, "resetValue"),
        reset_mask=_int(register_element, "resetMask"),
        description=_text(register_element, "description"),
        access=_access(register_element),
        fields=[_build_field(f, warnings) for f in register_element.findall("./fields/field")],
        dim=_dim(register_element, name, warnings),
    )


def _build_cluster(cluster_element: ET.Element, warnings: list[str]) -> Cluster:
    # Inside a cluster, registers and nested clusters are direct children: the
    # schema has no <registers> wrapper at this level.
    name = _text(cluster_element, "name") or ""
    return Cluster(
        name=name,
        address_offset=_int(cluster_element, "addressOffset", 0),
        description=_text(cluster_element, "description"),
        header_struct_name=_text(cluster_element, "headerStructName"),
        derived_from=cluster_element.get("derivedFrom"),  # XML attribute, as on a peripheral
        default_size=_int(cluster_element, "size"),
        default_access=_access(cluster_element),
        default_reset_value=_int(cluster_element, "resetValue"),
        default_reset_mask=_int(cluster_element, "resetMask"),
        registers=[_build_register(r, warnings) for r in cluster_element.findall("./register")],
        clusters=[_build_cluster(c, warnings) for c in cluster_element.findall("./cluster")],
        dim=_dim(cluster_element, name, warnings, cluster_element.get("derivedFrom") is not None),
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


def _build_interrupt(interrupt_element: ET.Element) -> Interrupt:
    return Interrupt(
        name=_text(interrupt_element, "name") or "",
        value=_int(interrupt_element, "value", 0),
        description=_text(interrupt_element, "description"),
    )


def _build_address_block(block_element: ET.Element) -> AddressBlock:
    return AddressBlock(
        offset=_int(block_element, "offset", 0),
        size=_int(block_element, "size", 0),
        usage=_text(block_element, "usage"),
    )


def _build_peripheral(peripheral_element: ET.Element, warnings: list[str]) -> Peripheral:
    name = _text(peripheral_element, "name") or ""
    return Peripheral(
        name=name,
        base_address=_int(peripheral_element, "baseAddress", 0),
        description=_text(peripheral_element, "description"),
        derived_from=peripheral_element.get("derivedFrom"),  # XML attribute, not a child
        group_name=_text(peripheral_element, "groupName"),
        header_struct_name=_text(peripheral_element, "headerStructName"),
        default_size=_int(peripheral_element, "size"),
        default_access=_access(peripheral_element),
        default_reset_value=_int(peripheral_element, "resetValue"),
        default_reset_mask=_int(peripheral_element, "resetMask"),
        registers=[
            _build_register(r, warnings) for r in peripheral_element.findall("./registers/register")
        ],
        interrupts=[_build_interrupt(i) for i in peripheral_element.findall("./interrupt")],
        address_blocks=[
            _build_address_block(b) for b in peripheral_element.findall("./addressBlock")
        ],
        clusters=[
            _build_cluster(c, warnings) for c in peripheral_element.findall("./registers/cluster")
        ],
        dim=_dim(
            peripheral_element, name, warnings, peripheral_element.get("derivedFrom") is not None
        ),
    )


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
        cpu_element = root.find("cpu")
        vendor_ext = root.find("vendorExtensions")
        return Device(
            name=_text(root, "name") or "device",
            description=_text(root, "description"),
            vendor=_text(root, "vendor"),
            series=_text(root, "series"),
            version=_text(root, "version"),
            license_text=_text(root, "licenseText"),
            header_prefix=_text(root, "headerDefinitionsPrefix"),
            # Preserve the vendor-extension subtree verbatim; never interpret it.
            vendor_extensions_xml=(
                ET.tostring(vendor_ext, encoding="unicode").strip()
                if vendor_ext is not None
                else None
            ),
            cpu=_build_cpu(cpu_element) if cpu_element is not None else None,
            address_unit_bits=_int(root, "addressUnitBits", DEFAULT_ADDRESS_UNIT_BITS),
            bus_width=_int(root, "width", DEFAULT_BUS_WIDTH),
            default_size=_int(root, "size"),
            default_access=_access(root),
            default_reset_value=_int(root, "resetValue"),
            default_reset_mask=_int(root, "resetMask"),
            peripherals=[
                _build_peripheral(p, self.warnings)
                for p in root.findall("./peripherals/peripheral")
            ],
        )

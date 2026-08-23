"""C writer.

Renders the intermediate representation into a C header of CMSIS-style
preprocessor definitions: a base-address macro per peripheral, a volatile
pointer accessor per register, position and mask macros per field, and a
constant per enumerated value.

The output style lives in an editable Jinja2 template
(``templates/c/header.h.j2``); this module only supplies the data and the
formatting helpers the template needs.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from ..ir import Access, Device, Peripheral, Register
from ..provenance import Provenance
from .base import EmitError, Writer

_TEMPLATE_DIR = Path(__file__).parent / "templates" / "c"

# --- C emitter constants ---
#: Bits in one byte; this emitter targets byte-addressable devices.
BITS_PER_BYTE = 8
#: Mask and hex-digit width for formatting 32-bit register values.
_UINT32_MASK = 0xFFFFFFFF
_HEX32_DIGITS = 8
#: Register base type keyed on width in bits. 64 is future-proofing (see TODO);
#: any size absent here is refused rather than rounded.
_C_TYPE = {8: "uint8_t", 16: "uint16_t", 32: "uint32_t", 64: "uint64_t"}
#: Register descriptions at most this long sit inline in the struct comment;
#: longer ones stay in the per-register banner so the layout stays a tight map.
_MAX_INLINE_DESC = 40


def _hex32(value: int) -> str:
    """Format ``value`` as a zero-padded 32-bit hexadecimal literal."""
    return f"0x{value & _UINT32_MASK:0{_HEX32_DIGITS}X}"


def _units_to_bytes(units: int, address_unit_bits: int) -> int:
    """Convert an address-unit count to bytes for this byte-addressed target.

    A no-op for byte-addressable devices; the conversion lives here, at the
    emitter, because a word-addressable target would convert differently (or
    not at all).
    """
    return units * address_unit_bits // BITS_PER_BYTE


def _short_desc(description: str | None) -> str:
    """A register description short enough to sit inline in the struct comment."""
    if description and len(description) <= _MAX_INLINE_DESC:
        return description
    return ""


def _member_type(register: Register) -> str:
    """A register's C storage type: volatile, and const when read-only.

    A read-only register becomes ``volatile const`` so writing it is a compile
    error (as CMSIS's ``__IM`` does). Write-only / read-write / write-once are
    plain ``volatile`` -- C has no type qualifier for "write-only" or "once".
    """
    const = "const " if register.access == Access.READ_ONLY else ""
    return f"volatile {const}{_C_TYPE[register.size]}"


def _peripheral_layout(peripheral: Peripheral, address_unit_bits: int) -> list[dict]:
    """Lay a peripheral's registers out as struct members, in offset order.

    Returns ordered entries -- each a register member or a reserved padding gap
    -- so the emitted struct places every register at its true offset.
    Overlapping registers cannot be represented as a plain struct and are
    refused (alternateRegister / union layouts are a later feature).
    """
    entries: list[dict] = []
    cursor = 0
    pad_index = 0
    for register in sorted(peripheral.registers, key=lambda r: r.address_offset):
        offset = _units_to_bytes(register.address_offset, address_unit_bits)
        if offset < cursor:
            raise EmitError(
                f"{peripheral.name}.{register.name}: register at offset 0x{offset:X} "
                "overlaps the preceding register (overlapping / alternateRegister "
                "layouts are not yet supported)"
            )
        if offset > cursor:
            entries.append(
                {
                    "offset": cursor,
                    "type": "uint8_t",
                    "field": f"RESERVED{pad_index}[{offset - cursor}];",
                    "desc": "(reserved)",
                    "member": None,
                }
            )
            pad_index += 1
        entries.append(
            {
                "offset": offset,
                "type": _member_type(register),
                "field": f"{register.name};",
                "desc": _short_desc(register.description),
                "member": register.name,
            }
        )
        cursor = offset + register.size // BITS_PER_BYTE
    return entries


class CWriter(Writer):
    """Writer that emits a C register header."""

    target_name = "c"
    file_extension = ".h"
    language = "C"

    def __init__(self) -> None:
        self._env = Environment(
            loader=FileSystemLoader(str(_TEMPLATE_DIR)),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
            autoescape=False,
        )
        self._env.filters["hex32"] = _hex32

    def render(self, device: Device, provenance: Provenance | None = None) -> str:
        """Render ``device`` into a C header string.

        Refuses non-byte-addressable devices rather than emitting byte offsets
        that would be silently wrong.
        """
        if device.address_unit_bits != BITS_PER_BYTE:
            raise EmitError(
                f"{device.name}: addressUnitBits={device.address_unit_bits} "
                "(word-addressable, e.g. TI C2000) is not supported by the C "
                "emitter yet -- offsets would be wrong if emitted as bytes."
            )
        for peripheral in device.peripherals:
            for register in peripheral.registers:
                if register.size not in _C_TYPE:
                    raise EmitError(
                        f"{peripheral.name}.{register.name}: register size "
                        f"{register.size} bits has no C type mapping "
                        f"(supported: {sorted(_C_TYPE)})"
                    )
        layouts = {
            id(peripheral): _peripheral_layout(peripheral, device.address_unit_bits)
            for peripheral in device.peripherals
        }
        template = self._env.get_template("header.h.j2")
        return template.render(
            device=device,
            provenance=provenance,
            prefix=device.header_prefix or "",
            to_bytes=lambda units: _units_to_bytes(units, device.address_unit_bits),
            member_type=_member_type,
            full_mask=lambda size: (1 << size) - 1,
            layout=lambda peripheral: layouts[id(peripheral)],
        )

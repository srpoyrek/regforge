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

from ..arch import NVIC_REGISTER_BANKS, is_cortex_m
from ..families import Family, group_families
from ..interrupts import all_interrupts, shared_vectors
from ..ir import Access, Device, Peripheral, Register
from ..layout import (
    BITS_PER_BYTE,
    LayoutError,
    asserted_struct_size,
    peripheral_layout,
    units_to_bytes,
)
from ..provenance import Provenance
from .base import EmitError, Writer

_TEMPLATE_DIR = Path(__file__).parent / "templates" / "c"

# --- C emitter constants ---
#: Mask and hex-digit width for formatting 32-bit register values.
_UINT32_MASK = 0xFFFFFFFF
_HEX32_DIGITS = 8
#: Register base type keyed on width in bits. 64 is future-proofing (see TODO);
#: any size absent here is refused rather than rounded.
_C_TYPE = {8: "uint8_t", 16: "uint16_t", 32: "uint32_t", 64: "uint64_t"}
#: Register descriptions at most this long sit inline in the struct comment;
#: longer ones stay in the per-register banner so the layout stays a tight map.
_MAX_INLINE_DESC = 40
#: Fallback element width, in bits, for a buffer window the bus width cannot
#: tile evenly. Bytes divide any window and are always representable.
_BUFFER_FALLBACK_BITS = 8


def _hex32(value: int) -> str:
    """Format ``value`` as a zero-padded 32-bit hexadecimal literal."""
    return f"0x{value & _UINT32_MASK:0{_HEX32_DIGITS}X}"


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
    assert register.size is not None  # size is resolved (and validated) before emission
    return f"volatile {const}{_C_TYPE[register.size]}"


def _type_aliases(family: Family, taken: set[str]) -> list[Peripheral]:
    """Instances of ``family`` that need a ``<name>_t`` alias for the shared type.

    Every peripheral should have a type spelled after itself, so a signature does
    not have to know that TIM2 and TIM3 share one layout. Two instances are
    skipped:

    * the one the type is *already* named after -- aliasing a typedef to itself
      is legal only from C11 on, and these headers must compile as C89;
    * one whose name another emitted type already claims. Nuvoton's M051 puts a
      peripheral called ``GPIO`` in the ``GPIO_GCR`` group while a separate
      ``GPIO`` group covers GP0..GP4, so the alias would redefine that group's
      type. The group owns the name; the alias gives way.
    """
    return [
        instance
        for instance in family.instances
        if instance.name.lower() != family.name.lower() and instance.name.lower() not in taken
    ]


def _alias_map(families: list[Family]) -> dict[int, list[Peripheral]]:
    """Per-family alias lists, resolved against every type name the header emits."""
    taken = {family.name.lower() for family in families}
    aliases: dict[int, list[Peripheral]] = {}
    for family in families:
        chosen = _type_aliases(family, taken)
        taken.update(instance.name.lower() for instance in chosen)
        aliases[id(family)] = chosen
    return aliases


def _buffer_element_bits(window_bytes: int, bus_width: int) -> int:
    """The element width, in bits, for a buffer window of ``window_bytes``.

    A ``buffer`` block is a range you stream through, so the natural element is
    one bus access -- the device's ``<width>``. The vendor gives no width for the
    window itself (``<addressBlock>`` carries only offset, size and usage), so
    the device's bus width is the closest thing to a declared answer. A window
    the bus width cannot tile evenly, or a width with no C type, falls back to
    bytes rather than rounding the window or dropping its tail.
    """
    if bus_width in _C_TYPE and window_bytes % (bus_width // BITS_PER_BYTE) == 0:
        return bus_width
    return _BUFFER_FALLBACK_BITS


def _c_layout(peripheral: Peripheral, address_unit_bits: int, bus_width: int) -> list[dict]:
    """Render the shared block layout into the C struct members the template needs.

    The offset / reserved-gap / overlap math is language-neutral and lives in
    :func:`regforge.layout.peripheral_layout`; this adapter only maps each slot
    to C syntax (``uint8_t`` padding, ``volatile`` member types, trailing ``;``).
    """
    try:
        size = asserted_struct_size(peripheral, address_unit_bits)
        slots = peripheral_layout(peripheral, address_unit_bits, pad_to_bytes=size)
    except LayoutError as error:  # surface as the writer's error type (CLI exit)
        raise EmitError(str(error)) from error
    entries: list[dict] = []
    pad_index = 0
    buffer_index = 0
    for slot in slots:
        if slot.buffer:
            bits = _buffer_element_bits(slot.gap_bytes, bus_width)
            name = f"BUFFER{buffer_index}"
            entries.append(
                {
                    "offset": slot.offset,
                    "type": f"volatile {_C_TYPE[bits]}",
                    "field": f"{name}[{slot.gap_bytes // (bits // BITS_PER_BYTE)}];",
                    "desc": "(buffer)",
                    "member": name,
                }
            )
            buffer_index += 1
        elif slot.is_reserved:
            entries.append(
                {
                    "offset": slot.offset,
                    "type": "uint8_t",
                    "field": f"RESERVED{pad_index}[{slot.gap_bytes}];",
                    "desc": "(reserved)",
                    "member": None,
                }
            )
            pad_index += 1
        else:
            register = slot.register
            assert register is not None  # a non-reserved slot always carries a register
            entries.append(
                {
                    "offset": slot.offset,
                    "type": _member_type(register),
                    "field": f"{register.name};",
                    "desc": _short_desc(register.description),
                    "member": register.name,
                }
            )
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
        families = group_families(device)
        aliases = _alias_map(families)
        layouts = {
            id(peripheral): _c_layout(peripheral, device.address_unit_bits, device.bus_width)
            for peripheral in device.peripherals
        }
        template = self._env.get_template("header.h.j2")
        return template.render(
            device=device,
            provenance=provenance,
            prefix=device.header_prefix or "",
            to_bytes=lambda units: units_to_bytes(units, device.address_unit_bits),
            member_type=_member_type,
            full_mask=lambda size: (1 << size) - 1,
            layout=lambda peripheral: layouts[id(peripheral)],
            struct_size=lambda peripheral: asserted_struct_size(
                peripheral, device.address_unit_bits
            ),
            families=families,
            type_aliases=lambda family: aliases[id(family)],
            interrupts=all_interrupts(device),
            shared_vectors=shared_vectors(device),
            is_cortex_m=is_cortex_m(device.cpu),
            nvic_banks=NVIC_REGISTER_BANKS,
        )

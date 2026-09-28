"""C writer.

Renders the intermediate representation into a C header of CMSIS-style
preprocessor definitions: a base-address macro per peripheral, one named
constant per member offset, stride and count, a volatile pointer accessor per
register built from those constants, position and mask macros per field, and
a constant per enumerated value. A cluster becomes a nested struct type; an
array (a register, cluster or field that kept its ``dim``) becomes one array
member with indexed accessor macros.

The output style lives in an editable Jinja2 template
(``templates/c/header.h.j2``); this module only supplies the data and the
formatting helpers the template needs.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from ..arch import NVIC_REGISTER_BANKS, is_cortex_m
from ..families import Family, cluster_signature, group_families
from ..interrupts import all_interrupts, shared_vectors
from ..ir import Access, Cluster, Device, Dim, Peripheral, Register, walk_clusters
from ..layout import (
    BITS_PER_BYTE,
    LayoutEntry,
    LayoutError,
    asserted_struct_size,
    peripheral_layout,
    registers_end,
    units_to_bytes,
)
from ..provenance import Provenance
from .base import EmitError, Writer

_TEMPLATE_DIR = Path(__file__).parent / "templates" / "c"

# --- C emitter constants ---
#: Mask and hex-digit width for formatting 32-bit register values.
_UINT32_MASK = 0xFFFFFFFF
_HEX32_DIGITS = 8
#: One past the last address a ``UL`` literal can hold; anything beyond is refused
#: rather than silently wrapped by :func:`_hex32`.
_ADDRESS_LIMIT = 1 << 32
#: Register base type keyed on width in bits. 64 is future-proofing (see TODO);
#: any size absent here is refused rather than rounded.
_C_TYPE = {8: "uint8_t", 16: "uint16_t", 32: "uint32_t", 64: "uint64_t"}
#: Register descriptions at most this long sit inline in the struct comment;
#: longer ones stay in the per-register banner so the layout stays a tight map.
_MAX_INLINE_DESC = 40
#: Fallback element width, in bits, for a buffer window the bus width cannot
#: tile evenly. Bytes divide any window and are always representable.
_BUFFER_FALLBACK_BITS = 8
#: Macro parameter names for array indices, outermost array first.
_INDEX_NAMES = "ijklmn"


def _hex32(value: int) -> str:
    """Format ``value`` as a zero-padded 32-bit hexadecimal literal."""
    return f"0x{value & _UINT32_MASK:0{_HEX32_DIGITS}X}"


def _short_desc(description: str | None) -> str:
    """A description short enough to sit inline in the struct comment."""
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


def _all_registers(peripheral: Peripheral) -> Iterator[Register]:
    """Every register of ``peripheral``, clusters included."""
    yield from peripheral.registers
    for _, cluster in walk_clusters(peripheral.clusters, peripheral.name):
        yield from cluster.registers


def _unexpanded_name(peripheral: Peripheral) -> str | None:
    """The first name still carrying a ``%s`` placeholder, if expansion was skipped."""
    if "%s" in peripheral.name:
        return peripheral.name
    for path, cluster in walk_clusters(peripheral.clusters, peripheral.name):
        if "%s" in cluster.name:
            return path
    for register in _all_registers(peripheral):
        if "%s" in register.name:
            return f"{peripheral.name}.{register.name}"
        for field_ in register.fields:
            if "%s" in field_.name:
                return f"{peripheral.name}.{register.name}.{field_.name}"
    return None


def _array_suffix(dim: Dim | None) -> str:
    """``[N]`` for an array of N elements, nothing for a single one."""
    return f"[{dim.length}]" if dim is not None else ""


def _count_suffix(spf: str, member: str, count: int) -> str:
    """``[<SPF>_<MEMBER>_COUNT]`` for a packed array slot, nothing for a single member."""
    return f"[{spf}_{member.upper()}_COUNT]" if count > 1 else ""


def _c_layout(
    entries: list[LayoutEntry], cluster_names: dict[int, str], bus_width: int, spf: str
) -> list[dict]:
    """Render layout slots into the C struct members the template needs.

    The offset / reserved-gap / overlap math is language-neutral and lives in
    :mod:`regforge.layout`; this adapter only maps each slot to C syntax
    (``uint8_t`` padding, ``volatile`` member types, the nested type for a
    cluster, trailing ``;``). Every array bound is a layout constant of the
    type ``spf`` names -- ``_COUNT`` for arrays and buffer windows, ``_SIZE``
    for padding -- so the struct carries no literal number.
    """
    entries_out: list[dict] = []
    pad_index = 0
    buffer_index = 0
    for slot in entries:
        if slot.buffer:
            bits = _buffer_element_bits(slot.gap_bytes, bus_width)
            name = f"BUFFER{buffer_index}"
            entries_out.append(
                {
                    "offset": slot.offset,
                    "type": f"volatile {_C_TYPE[bits]}",
                    "field": f"{name}[{spf}_{name}_COUNT];",
                    "desc": "(buffer)",
                    "member": name,
                    "elements": 1,
                    "bytes": slot.size_bytes,
                    "stem": None,
                    "index": None,
                }
            )
            buffer_index += 1
        elif slot.is_reserved:
            name = f"RESERVED{pad_index}"
            entries_out.append(
                {
                    "offset": slot.offset,
                    "type": "uint8_t",
                    "field": f"{name}[{spf}_{name}_SIZE];",
                    "desc": "(reserved)",
                    "member": None,
                    "elements": 1,
                    "bytes": slot.size_bytes,
                    "stem": None,
                    "index": None,
                }
            )
            pad_index += 1
        elif slot.cluster is not None:
            cluster = slot.cluster
            entries_out.append(
                {
                    "offset": slot.offset,
                    "type": cluster_names[id(cluster)],
                    "field": f"{cluster.name}{_count_suffix(spf, cluster.name, slot.count)};",
                    "desc": _short_desc(cluster.description),
                    "member": cluster.name,
                    "elements": slot.count,
                    "bytes": slot.size_bytes,
                    "stem": None,
                    "index": None,
                }
            )
        else:
            register = slot.register
            assert register is not None  # a non-reserved slot always carries a member
            name = slot.name or register.name  # an unpacked array's element has its own
            entries_out.append(
                {
                    "offset": slot.offset,
                    "type": _member_type(register),
                    "field": f"{name}{_count_suffix(spf, register.name, slot.count)};",
                    "desc": _short_desc(register.description),
                    "member": name,
                    "elements": slot.count,
                    "bytes": slot.size_bytes,
                    "stem": register.name if slot.index is not None else None,
                    "index": slot.index,
                }
            )
    return entries_out


def _unique_type_name(candidates: list[str], taken: set[str]) -> str:
    """The first candidate not yet emitted, else the first with a numeric suffix."""
    for candidate in candidates:
        if candidate not in taken:
            taken.add(candidate)
            return candidate
    base = candidates[0][: -len("_t")]
    index = 2
    while f"{base}_{index}_t" in taken:
        index += 1
    name = f"{base}_{index}_t"
    taken.add(name)
    return name


def _cluster_types(
    entries: list[LayoutEntry],
    label: str,
    tag_prefix: str,
    type_base: str,
    taken: set[str],
    cluster_names: dict[int, str],
    cluster_tags: dict[int, str],
    shared: dict[tuple, tuple[str, str]],
    bus_width: int,
) -> list[dict]:
    """The cluster struct types a block uses, innermost first, each emitted once.

    A cluster's type is spelled after the enclosing family and the cluster's
    ``headerStructName`` (else its own name), so vendors calling every channel
    block ``CH`` never collide across peripherals; a nested cluster appends its
    name to its parent's. Clusters that want the same name *and* have the same
    contents -- the copies expanded from ``CH%s``, or one vendor block placed
    twice -- share a single type. Two that want the same name with different
    contents fall back to the cluster's own name, then to a numeric suffix.
    The assert tags and the layout constants of a type follow the name that
    was actually chosen, so a fallback never reuses another type's. Nested
    types come first in the list so each is defined before its user.
    """
    types: list[dict] = []
    for slot in entries:
        cluster = slot.cluster
        if cluster is None:
            continue
        wanted = cluster.header_struct_name or cluster.name
        key = (f"{type_base}_{wanted.lower()}", cluster_signature(cluster)[2:])
        if key in shared:
            cluster_names[id(cluster)], cluster_tags[id(cluster)] = shared[key]
            continue
        candidates = [f"{type_base}_{wanted.lower()}_t"]
        if wanted.lower() != cluster.name.lower():
            candidates.append(f"{type_base}_{cluster.name.lower()}_t")
        type_name = _unique_type_name(candidates, taken)
        inner_base = type_name[: -len("_t")]
        inner_tag = f"{tag_prefix}{inner_base[len(type_base):].upper()}"
        inner_label = f"{label}.{wanted}"
        shared[key] = (type_name, inner_tag)
        cluster_names[id(cluster)] = type_name
        cluster_tags[id(cluster)] = inner_tag
        types += _cluster_types(
            slot.members,
            inner_label,
            inner_tag,
            inner_base,
            taken,
            cluster_names,
            cluster_tags,
            shared,
            bus_width,
        )
        types.append(
            {
                "tname": type_name,
                "spf": inner_tag,
                "own": f"{tag_prefix}_{cluster.name.upper()}",
                "label": inner_label,
                "desc": cluster.description,
                "members": _c_layout(slot.members, cluster_names, bus_width, inner_tag),
                "element_bytes": slot.element_bytes,
                "count": cluster.dim.length if cluster.dim is not None else None,
            }
        )
    return types


def _constants(
    spf: str,
    entries: list[LayoutEntry],
    address_unit_bits: int,
    bus_width: int,
    cluster_tags: dict[int, str],
    emitted: set[str],
) -> list[dict]:
    """The named numbers of one struct type, in member order.

    Every member gets ``<TYPE>_<MEMBER>_OFFSET``; an array adds ``_STRIDE`` and
    ``_COUNT``; a buffer window adds ``_COUNT`` (bus words); a padding gap is
    ``_RESERVED<n>_SIZE`` (bytes). So every array bound in the struct is a
    name. A cluster's own offset (and stride) is named after the cluster,
    and its members after the cluster's *type*, relative to one element, so
    copies of one type share one set, emitted once. Every assert and accessor
    the header emits refers to these, so each number is written exactly once.
    """
    constants: list[dict] = []
    buffer_index = 0
    pad_index = 0
    seen: set[int] = set()
    for slot in entries:
        if slot.buffer:
            stem = f"{spf}_BUFFER{buffer_index}"
            bits = _buffer_element_bits(slot.gap_bytes, bus_width)
            count = slot.gap_bytes // (bits // BITS_PER_BYTE)
            constants.append({"name": f"{stem}_OFFSET", "value": f"{_hex32(slot.offset)}UL"})
            constants.append({"name": f"{stem}_COUNT", "value": f"{count}U"})
            buffer_index += 1
        elif slot.is_reserved:
            stem = f"{spf}_RESERVED{pad_index}"
            constants.append({"name": f"{stem}_SIZE", "value": f"{_hex32(slot.gap_bytes)}UL"})
            pad_index += 1
        elif slot.register is not None:
            register = slot.register
            if id(register) in seen:
                continue  # an unpacked array is several slots but one set of constants
            seen.add(id(register))
            stem = f"{spf}_{register.name.upper()}"
            offset = units_to_bytes(register.address_offset, address_unit_bits)
            constants.append({"name": f"{stem}_OFFSET", "value": f"{_hex32(offset)}UL"})
            if register.dim is not None:
                stride = units_to_bytes(register.dim.stride, address_unit_bits)
                constants.append({"name": f"{stem}_STRIDE", "value": f"{_hex32(stride)}UL"})
                constants.append({"name": f"{stem}_COUNT", "value": f"{register.dim.length}U"})
        elif slot.cluster is not None:
            cluster = slot.cluster
            own = f"{spf}_{cluster.name.upper()}"
            constants.append({"name": f"{own}_OFFSET", "value": f"{_hex32(slot.offset)}UL"})
            if cluster.dim is not None:
                constants.append(
                    {"name": f"{own}_STRIDE", "value": f"{_hex32(slot.element_bytes)}UL"}
                )
                constants.append({"name": f"{own}_COUNT", "value": f"{slot.count}U"})
            type_stem = cluster_tags[id(cluster)]
            if type_stem not in emitted:
                emitted.add(type_stem)
                constants += _constants(
                    type_stem, slot.members, address_unit_bits, bus_width, cluster_tags, emitted
                )
    return constants


def _accessors(peripheral: Peripheral, spf: str, cluster_tags: dict[int, str]) -> list[dict]:
    """Every register reachable from ``peripheral`` as a flat macro: name, indices, address.

    A register inside a cluster is reached through the cluster's name
    (``CH_CTRL``); every array on the path adds one macro parameter, outermost
    first (``(i, j)``), and one ``(index) * <STEM>_STRIDE`` term. The address
    is a sum of the family's layout constants, never a literal, so a plain
    register reads ``BASE + DC_UART_DR_OFFSET``.
    """
    result: list[dict] = []

    def stride_term(stem: str, params: list[str]) -> str:
        index = _INDEX_NAMES[len(params)]
        params.append(index)
        return f"({index}) * {stem}_STRIDE"

    def visit(
        register: Register,
        names: list[str],
        labels: list[str],
        params: list[str],
        terms: list[str],
        type_stem: str,
    ) -> None:
        params = list(params)
        stem = f"{type_stem}_{register.name.upper()}"
        terms = [*terms, f"{stem}_OFFSET"]
        if register.dim is not None:
            terms.append(stride_term(stem, params))
        result.append(
            {
                "name": "_".join([*names, register.name]),
                "label": ".".join([*labels, register.name + _array_suffix(register.dim)]),
                "params": f"({', '.join(params)})" if params else "",
                "address": " + ".join(terms),
                "register": register,
                "count": f"{stem}_COUNT" if register.dim is not None else None,
            }
        )

    def walk(
        clusters: list[Cluster],
        names: list[str],
        labels: list[str],
        params: list[str],
        terms: list[str],
        type_stem: str,
    ) -> None:
        for cluster in clusters:
            own = f"{type_stem}_{cluster.name.upper()}"
            inner_params = list(params)
            inner_terms = [*terms, f"{own}_OFFSET"]
            if cluster.dim is not None:
                inner_terms.append(stride_term(own, inner_params))
            inner_type = cluster_tags[id(cluster)]
            inner_names = [*names, cluster.name]
            inner_labels = [*labels, cluster.name + _array_suffix(cluster.dim)]
            for register in cluster.registers:
                visit(register, inner_names, inner_labels, inner_params, inner_terms, inner_type)
            walk(cluster.clusters, inner_names, inner_labels, inner_params, inner_terms, inner_type)

    for register in peripheral.registers:
        visit(register, [], [], [], [], spf)
    walk(peripheral.clusters, [], [], [], [], spf)
    return result


def _array_indices(peripheral: Peripheral) -> list[dict]:
    """Every kept array of ``peripheral`` that names its indices (``dimArrayIndex``).

    Registers and clusters at any depth, each as the macro stem the accessors
    use (``CH`` or ``CH_BUF``), a label for the comment, and the named values.
    """
    result: list[dict] = []

    def note(dim: Dim | None, names: list[str], labels: list[str]) -> None:
        if dim is not None and dim.array and dim.array_index:
            result.append(
                {"name": "_".join(names), "label": ".".join(labels), "names": dim.array_index}
            )

    def walk(clusters: list[Cluster], names: list[str], labels: list[str]) -> None:
        for cluster in clusters:
            inner_names = [*names, cluster.name]
            inner_labels = [*labels, cluster.name + _array_suffix(cluster.dim)]
            note(cluster.dim, inner_names, inner_labels)
            for register in cluster.registers:
                note(
                    register.dim,
                    [*inner_names, register.name],
                    [*inner_labels, register.name + _array_suffix(register.dim)],
                )
            walk(cluster.clusters, inner_names, inner_labels)

    for register in peripheral.registers:
        note(register.dim, [register.name], [register.name + _array_suffix(register.dim)])
    walk(peripheral.clusters, [], [])
    return result


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
        that would be silently wrong, a device that was never expanded (a name
        still holding ``%s``), and any register size with no C type.
        """
        unit_bits = device.address_unit_bits
        if unit_bits != BITS_PER_BYTE:
            raise EmitError(
                f"{device.name}: addressUnitBits={unit_bits} "
                "(word-addressable, e.g. TI C2000) is not supported by the C "
                "emitter yet -- offsets would be wrong if emitted as bytes."
            )
        for peripheral in device.peripherals:
            unexpanded = _unexpanded_name(peripheral)
            if unexpanded is not None:
                raise EmitError(
                    f"{unexpanded}: name still holds a %s placeholder -- run "
                    "expand_dim before rendering"
                )
            for register in _all_registers(peripheral):
                if register.size is None or register.size not in _C_TYPE:
                    raise EmitError(
                        f"{peripheral.name}.{register.name}: register size "
                        f"{register.size} bits has no C type mapping "
                        f"(supported: {sorted(_C_TYPE)})"
                    )
                for field_ in register.fields:
                    end = field_.bit_offset + field_.bit_width
                    if field_.dim is not None:
                        end += (field_.dim.length - 1) * field_.dim.stride
                    if end > register.size:
                        # hex32 would wrap the mask; refuse by name instead.
                        raise EmitError(
                            f"{peripheral.name}.{register.name}.{field_.name}: bits "
                            f"{field_.bit_offset}..{end - 1} run past the {register.size}-bit "
                            "register -- its mask cannot be emitted"
                        )
            base = units_to_bytes(peripheral.base_address, unit_bits)
            end = base + registers_end(peripheral, unit_bits)
            for block in peripheral.address_blocks:
                end = max(end, base + units_to_bytes(block.offset + block.size, unit_bits))
            if end > _ADDRESS_LIMIT:
                raise EmitError(
                    f"{peripheral.name}: reaches {end:#x}, past the 32-bit address space "
                    "this writer's literals can hold"
                )

        prefix = device.header_prefix or ""
        families = group_families(device)
        aliases = _alias_map(families)
        # Every type name the header emits, so cluster types can stay unique.
        taken_types = {f"{prefix.lower()}{family.name.lower()}_t" for family in families}
        taken_types |= {
            f"{prefix.lower()}{instance.name.lower()}_t"
            for chosen in aliases.values()
            for instance in chosen
        }
        cluster_names: dict[int, str] = {}
        cluster_tags: dict[int, str] = {}
        shared_clusters: dict[tuple, tuple[str, str]] = {}
        cluster_types: dict[int, list[dict]] = {}
        layouts: dict[int, list[dict]] = {}
        constants: dict[int, list[dict]] = {}
        accessors: dict[int, list[dict]] = {}
        for family in families:
            source = family.type_source
            spf = f"{prefix}{family.name.upper()}"
            try:
                size = asserted_struct_size(source, unit_bits)
                entries = peripheral_layout(source, unit_bits, pad_to_bytes=size)
            except LayoutError as error:  # surface as the writer's error type (CLI exit)
                raise EmitError(str(error)) from error
            cluster_types[id(family)] = _cluster_types(
                entries,
                family.name,
                spf,
                f"{prefix.lower()}{family.name.lower()}",
                taken_types,
                cluster_names,
                cluster_tags,
                shared_clusters,
                device.bus_width,
            )
            layouts[id(source)] = _c_layout(entries, cluster_names, device.bus_width, spf)
            family_constants = _constants(
                spf, entries, unit_bits, device.bus_width, cluster_tags, set()
            )
            if size is not None:
                family_constants.append({"name": f"{spf}_SIZE", "value": f"{_hex32(size)}UL"})
            constants[id(family)] = family_constants
            # Instances of a family share its layout, so one accessor list serves all.
            accessors[id(family)] = _accessors(source, spf, cluster_tags)
        array_indices = {id(p): _array_indices(p) for p in device.peripherals}

        template = self._env.get_template("header.h.j2")
        return template.render(
            device=device,
            provenance=provenance,
            prefix=prefix,
            to_bytes=lambda units: units_to_bytes(units, unit_bits),
            member_type=_member_type,
            full_mask=lambda size: (1 << size) - 1,
            layout=lambda peripheral: layouts[id(peripheral)],
            cluster_types=lambda family: cluster_types[id(family)],
            constants=lambda family: constants[id(family)],
            accessors=lambda family: accessors[id(family)],
            array_indices=lambda peripheral: array_indices[id(peripheral)],
            struct_size=lambda peripheral: asserted_struct_size(peripheral, unit_bits),
            families=families,
            type_aliases=lambda family: aliases[id(family)],
            interrupts=all_interrupts(device),
            shared_vectors=shared_vectors(device),
            is_cortex_m=is_cortex_m(device.cpu),
            nvic_banks=NVIC_REGISTER_BANKS,
        )

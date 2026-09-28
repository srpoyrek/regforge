"""Register-block layout shared across output writers.

Turning a peripheral's registers into an ordered sequence of members and the
reserved gaps between them -- with overlap detection -- is structural, not
language-specific: a C struct, a Rust ``#[repr(C)]`` struct, and a C++ struct all
need the same offsets and the same padding. This module computes that abstract
layout once; each writer maps :class:`LayoutEntry` values to its own type syntax.

A cluster is laid out the same way, one level down: it takes one slot in its
parent and carries the layout of its own members. An array -- a register or
cluster whose ``dim`` is still set after expansion -- is one slot sized for
every element when its elements are packed, so a writer can spell it as a
single array member; a register array with holes between its elements becomes
one slot per element, since no language array can hold the holes.

Address-unit conversion lives here too, for the same reason: offsets are stored
in the device's address units, and turning them into bytes is a target-model
concern any byte-addressable writer shares (a word-addressable target would
convert differently -- which is exactly why it is a function, not a hardcode).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .ir import AddressBlock, Cluster, Peripheral, Register

#: Bits in one byte. The layout math and every byte-addressable writer share it.
BITS_PER_BYTE = 8


class LayoutError(Exception):
    """Raised when a register block cannot form a linear layout."""


def units_to_bytes(units: int, address_unit_bits: int) -> int:
    """Convert an address-unit count to bytes.

    A no-op for byte-addressable devices (``address_unit_bits == 8``); a
    word-addressable target (e.g. TI C2000 at 16) converts differently, which is
    why callers go through this helper instead of assuming bytes.
    """
    return units * address_unit_bits // BITS_PER_BYTE


@dataclass
class LayoutEntry:
    """One slot in a register block: a register, a cluster, a reserved gap, or a buffer window.

    A ``buffer`` addressBlock is a range the vendor deliberately left unnamed --
    a FIFO or packet window you stream through rather than a set of registers --
    so it occupies the struct as one raw array instead of named members. A
    cluster slot carries the layout of its own members. An array slot (a
    register or cluster whose ``dim`` is set) spans every element when it is
    packed; a register array with holes between its elements is one slot per
    element instead, each named after the element (``CH0``, ``CH1``, ...).

    Attributes:
        offset: Byte offset of the slot from the block base.
        register: The register at this offset, or ``None`` for anything else.
        gap_bytes: Size in bytes of a reserved gap or a buffer window (``0`` for
            a register or cluster member).
        buffer: Whether the slot is a declared ``buffer`` block rather than padding.
        cluster: The cluster at this offset, or ``None`` for anything else.
        element_bytes: Size in bytes of one element of a register or cluster
            slot -- an array's stride.
        size_bytes: Bytes the whole slot occupies: every element of an array,
            the gap, or the window.
        count: Elements in the slot: a packed array's ``dim`` count, else 1.
        name: The member's name when it differs from the register's -- one
            element of an unpacked array; ``None`` otherwise.
        index: That element's position in its array; ``None`` otherwise.
        members: A cluster's own layout, padded to ``element_bytes``; empty for
            every other kind of slot.
    """

    offset: int
    register: Register | None
    gap_bytes: int = 0
    buffer: bool = False
    cluster: Cluster | None = None
    element_bytes: int = 0
    size_bytes: int = 0
    count: int = 1
    name: str | None = None
    index: int | None = None
    members: list[LayoutEntry] = field(default_factory=list)

    @property
    def is_reserved(self) -> bool:
        """Whether this slot is reserved padding rather than a member or a window."""
        return self.register is None and self.cluster is None and not self.buffer

    @property
    def label(self) -> str:
        """What to call the slot in a message: the member name, or what it holds."""
        if self.register is not None:
            return self.name or self.register.name
        if self.cluster is not None:
            return self.cluster.name
        return "buffer" if self.buffer else "reserved"


def struct_block(peripheral: Peripheral) -> AddressBlock | None:
    """The single ``registers`` block that defines the struct's size, or ``None``.

    Only the register windows are considered: a ``buffer`` block is emitted as a
    member and a ``reserved`` block as padding, so neither costs the peripheral
    its size contract. What still yields no contract is a peripheral with no
    block, with several register windows, or whose window does not start at
    offset 0 (handled by later work), and a zero-size window, which would assert
    a struct size of 0.
    """
    blocks = [block for block in peripheral.address_blocks if block.holds_registers]
    if len(blocks) != 1:
        return None
    block = blocks[0]
    if block.offset != 0 or block.size <= 0:
        return None
    return block


# --- extents: how far a member reaches, without validating its layout ---


def _element_bytes(register: Register) -> int:
    return (register.size or 0) // BITS_PER_BYTE


def _stride_units(count: int, increment: int) -> int:
    """Address units from the first element's start to the last element's start."""
    return (count - 1) * increment


def register_span_units(register: Register, address_unit_bits: int) -> int:
    """Address units from a register's offset to the end of its last element."""
    units = (register.size or 0) // address_unit_bits
    if register.dim is not None:
        units += _stride_units(register.dim.length, register.dim.stride)
    return units


def register_span_bytes(register: Register, address_unit_bits: int) -> int:
    """Bytes from a register's offset to the end of its last element."""
    span = _element_bytes(register)
    if register.dim is not None:
        stride = _stride_units(register.dim.length, register.dim.stride)
        span += units_to_bytes(stride, address_unit_bits)
    return span


def cluster_element_units(cluster: Cluster, address_unit_bits: int) -> int:
    """Address units one element of ``cluster`` reaches, from its own start."""
    end = 0
    for register in cluster.registers:
        end = max(end, register.address_offset + register_span_units(register, address_unit_bits))
    for inner in cluster.clusters:
        end = max(end, inner.address_offset + cluster_span_units(inner, address_unit_bits))
    return end


def cluster_span_units(cluster: Cluster, address_unit_bits: int) -> int:
    """Address units from a cluster's offset to the end of its last element."""
    span = cluster_element_units(cluster, address_unit_bits)
    if cluster.dim is not None:
        span += _stride_units(cluster.dim.length, cluster.dim.stride)
    return span


def cluster_span_bytes(cluster: Cluster, address_unit_bits: int) -> int:
    """Bytes from a cluster's offset to the end of its last element."""
    end = 0
    for register in cluster.registers:
        offset = units_to_bytes(register.address_offset, address_unit_bits)
        end = max(end, offset + register_span_bytes(register, address_unit_bits))
    for inner in cluster.clusters:
        offset = units_to_bytes(inner.address_offset, address_unit_bits)
        end = max(end, offset + cluster_span_bytes(inner, address_unit_bits))
    if cluster.dim is not None:
        stride = _stride_units(cluster.dim.length, cluster.dim.stride)
        end += units_to_bytes(stride, address_unit_bits)
    return end


def registers_end(peripheral: Peripheral, address_unit_bits: int) -> int:
    """The byte offset just past the peripheral's last register or cluster element."""
    end = 0
    for register in peripheral.registers:
        offset = units_to_bytes(register.address_offset, address_unit_bits)
        end = max(end, offset + register_span_bytes(register, address_unit_bits))
    for cluster in peripheral.clusters:
        offset = units_to_bytes(cluster.address_offset, address_unit_bits)
        end = max(end, offset + cluster_span_bytes(cluster, address_unit_bits))
    return end


def asserted_struct_size(peripheral: Peripheral, address_unit_bits: int) -> int | None:
    """The struct size (bytes) to static-assert from the addressBlock, or ``None``.

    With a clean ``registers`` block (see :func:`struct_block`) that *covers* the
    registers, the size is the block size -- the struct is padded to it, so the
    assert is an equality contract and array stride is correct. If the block is
    *smaller* than the registers (a vendor bug), the honest floor is the natural
    register-derived size (and :mod:`regforge.check` flags the bad block). Without
    a clean block, there is no contract -- ``None``.

    Every other declared block extends the contract too: a ``buffer`` window is a
    member and a ``reserved`` range is padding, so both are inside the struct and
    ``sizeof`` has to reach past them.
    """
    block = struct_block(peripheral)
    if block is None:
        return None
    end = max(
        units_to_bytes(block.size, address_unit_bits),
        registers_end(peripheral, address_unit_bits),
    )
    for other in peripheral.address_blocks:
        end = max(end, units_to_bytes(other.offset + other.size, address_unit_bits))
    return end


# --- layout: slots in offset order, gaps filled, overlaps refused ---


def _end(entries: list[LayoutEntry]) -> int:
    return entries[-1].offset + entries[-1].size_bytes if entries else 0


def _register_slots(where: str, register: Register, address_unit_bits: int) -> list[LayoutEntry]:
    """A register's slot, or one slot per element for an array that is not packed.

    ``NAME[%s]`` asks for an array. When the stride equals the element size
    that is one packed array member. When the stride is larger there are holes
    between the elements, and a language array cannot hold them, so each
    element becomes a member of its own (``CH0``, ``CH1``, ...) with the holes
    as padding; an indexed accessor macro still reaches element ``i`` at its
    true stride. A stride smaller than the element means the elements overlap,
    which no linear layout can express.
    """
    offset = units_to_bytes(register.address_offset, address_unit_bits)
    element = _element_bytes(register)
    if register.dim is None:
        return [
            LayoutEntry(offset=offset, register=register, element_bytes=element, size_bytes=element)
        ]
    count = register.dim.length
    stride = units_to_bytes(register.dim.stride, address_unit_bits)
    if stride < element:
        raise LayoutError(
            f"{where}.{register.name}[{count}]: stride {stride} byte(s) is smaller than the "
            f"element size {element} -- the elements overlap"
        )
    if stride == element:
        return [
            LayoutEntry(
                offset=offset,
                register=register,
                element_bytes=element,
                size_bytes=element * count,
                count=count,
            )
        ]
    return [
        LayoutEntry(
            offset=offset + index * stride,
            register=register,
            element_bytes=element,
            size_bytes=element,
            name=f"{register.name}{index}",
            index=index,
        )
        for index in range(count)
    ]


def _cluster_slot(where: str, cluster: Cluster, address_unit_bits: int) -> LayoutEntry:
    members = cluster_layout(cluster, address_unit_bits, where)
    element = _end(members)
    count = cluster.dim.length if cluster.dim is not None else 1
    return LayoutEntry(
        offset=units_to_bytes(cluster.address_offset, address_unit_bits),
        register=None,
        cluster=cluster,
        element_bytes=element,
        size_bytes=element * count,
        count=count,
        members=members,
    )


def _block_layout(
    where: str,
    registers: list[Register],
    clusters: list[Cluster],
    buffers: list[AddressBlock],
    address_unit_bits: int,
    pad_to_bytes: int | None,
) -> list[LayoutEntry]:
    slots: list[LayoutEntry] = []
    for register in registers:
        slots += _register_slots(where, register, address_unit_bits)
    slots += [_cluster_slot(where, cluster, address_unit_bits) for cluster in clusters]
    for block in buffers:
        size = units_to_bytes(block.size, address_unit_bits)
        slots.append(
            LayoutEntry(
                offset=units_to_bytes(block.offset, address_unit_bits),
                register=None,
                gap_bytes=size,
                buffer=True,
                size_bytes=size,
            )
        )

    entries: list[LayoutEntry] = []
    cursor = 0
    # Sort on the offset alone: two slots at one offset must not fall through to
    # comparing the entries themselves, which are not orderable.
    for slot in sorted(slots, key=lambda entry: entry.offset):
        if slot.offset < cursor:
            if slot.register is not None:
                what = f"{where}.{slot.label}: register"
            elif slot.cluster is not None:
                what = f"{where}.{slot.label}: cluster"
            else:
                what = f"{where}: buffer addressBlock"
            raise LayoutError(
                f"{what} at offset 0x{slot.offset:X} overlaps the preceding member "
                "(overlapping / alternateRegister layouts are not yet supported)"
            )
        if slot.offset > cursor:
            gap = slot.offset - cursor
            entries.append(LayoutEntry(offset=cursor, register=None, gap_bytes=gap, size_bytes=gap))
        entries.append(slot)
        cursor = slot.offset + slot.size_bytes
    if pad_to_bytes is not None and pad_to_bytes > cursor:
        gap = pad_to_bytes - cursor
        entries.append(LayoutEntry(offset=cursor, register=None, gap_bytes=gap, size_bytes=gap))
    return entries


def cluster_layout(cluster: Cluster, address_unit_bits: int, where: str = "") -> list[LayoutEntry]:
    """One cluster element's members, in offset order with padding.

    An array cluster's element is padded out to the stride, so ``count`` of them
    tile the array exactly and a writer can spell it as one array of the element
    struct. A stride smaller than the contents means the elements overlap, which
    no linear layout can express, and raises :class:`LayoutError`; so does an
    empty cluster, which has no element to lay out (a cluster ``derivedFrom`` is
    not resolved yet).
    """
    path = f"{where}.{cluster.name}" if where else cluster.name
    if not cluster.registers and not cluster.clusters:
        raise LayoutError(
            f"{path}: cluster has no registers (a cluster derivedFrom is not resolved yet)"
        )
    members = _block_layout(path, cluster.registers, cluster.clusters, [], address_unit_bits, None)
    if cluster.dim is not None:
        natural = _end(members)
        stride = units_to_bytes(cluster.dim.stride, address_unit_bits)
        if stride < natural:
            raise LayoutError(
                f"{path}[{cluster.dim.length}]: stride 0x{stride:X} is smaller than the "
                f"cluster's contents (0x{natural:X}) -- the elements overlap"
            )
        if stride > natural:
            gap = stride - natural
            members.append(
                LayoutEntry(offset=natural, register=None, gap_bytes=gap, size_bytes=gap)
            )
    return members


def cluster_element_bytes(cluster: Cluster, address_unit_bits: int, where: str = "") -> int:
    """Size in bytes of one element of ``cluster``: its contents, padded to the stride."""
    return _end(cluster_layout(cluster, address_unit_bits, where))


def peripheral_layout(
    peripheral: Peripheral, address_unit_bits: int, pad_to_bytes: int | None = None
) -> list[LayoutEntry]:
    """Order a peripheral's registers, clusters and buffer windows into slots, by offset.

    Every register's size must already be resolved. A ``buffer`` addressBlock
    takes its place among the registers by offset and occupies the struct as one
    unnamed window. Overlapping slots cannot be represented as a linear block and
    raise :class:`LayoutError` (union / alternateRegister layouts are a later
    feature). When ``pad_to_bytes`` exceeds the last slot's end, a trailing
    reserved gap fills the struct out to that size (so ``sizeof`` matches the
    declared addressBlock).
    """
    buffers = [block for block in peripheral.address_blocks if block.is_buffer]
    return _block_layout(
        peripheral.name,
        peripheral.registers,
        peripheral.clusters,
        buffers,
        address_unit_bits,
        pad_to_bytes,
    )

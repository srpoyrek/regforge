"""Intermediate representation of a device register map.

The intermediate representation (IR) is the format-independent data model at
the centre of regforge. Input readers parse a source description into these
dataclasses, and output writers render them into a target language. Neither
side depends on the other: adding an input format or an output language only
touches its own package.

The hierarchy mirrors the structure of a memory-mapped device:

``Device`` -> ``Peripheral`` -> (``Cluster`` ->) ``Register`` -> ``Field`` -> ``EnumeratedValue``
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import Enum

# --- SVD schema defaults (used when the source omits an optional element) ---
#: Default bits per address unit (8 => byte-addressable).
DEFAULT_ADDRESS_UNIT_BITS = 8
#: Default data bus width in bits (SVD ``<width>``; also the register-size
#: last resort in the defaults resolution pass).
DEFAULT_BUS_WIDTH = 32


class Access(Enum):
    """Register/field access policy, spelled as in SVD."""

    READ_ONLY = "read-only"
    WRITE_ONLY = "write-only"
    READ_WRITE = "read-write"
    WRITE_ONCE = "writeOnce"
    READ_WRITE_ONCE = "read-writeOnce"


@dataclass
class EnumeratedValue:
    """A named constant that a :class:`Field` may hold.

    Attributes:
        name: Identifier of the value, e.g. ``"OUTPUT"``.
        value: The numeric value written to the field.
        description: Optional human-readable description.
    """

    name: str
    value: int
    description: str | None = None


@dataclass
class Dim:
    """An array of copies (SVD ``<dim>``, ``<dimIncrement>``, ``<dimIndex>``).

    A peripheral, cluster, register or field carrying a ``Dim`` is a template:
    ``count`` copies of it exist, ``increment`` apart, and each copy's name is
    the template's name with ``%s`` replaced by one of :attr:`labels`. The
    reader stores it as parsed; :func:`regforge.resolve.expand_dim` turns a
    ``%s`` template into its copies, and keeps a ``[%s]`` template as one
    element with ``dim`` still set so a writer can emit it as an array.

    Attributes:
        count: Number of copies (``<dim>``).
        increment: Distance between the starts of two neighbouring copies
            (``<dimIncrement>``): address units for a peripheral, cluster or
            register, like every other offset in the IR; bits for a field.
            ``None`` when the source omits it: expansion reports that and
            keeps one instance, so no ``Dim`` that survives expansion lacks it.
        index: The labels that replace ``%s``, in order (``<dimIndex>``);
            ``None`` when the source omits it and the copies are numbered from 0.
        array: Whether the template stays one array element (``NAME[%s]``)
            instead of expanding into copies. Set by expansion; a ``Dim`` that
            survives expansion always carries it.
        name: A name for the element type the copies share (``<dimName>``);
            ranks below ``headerStructName`` and above ``groupName`` when a
            type is named. ``None`` when absent.
        array_index: Names for the indices of an array (``<dimArrayIndex>``),
            each an :class:`EnumeratedValue`; empty when absent. A writer may
            emit them as index constants beside the array.
    """

    count: int
    increment: int | None
    index: list[str] | None = None
    array: bool = False
    name: str | None = None
    array_index: list[EnumeratedValue] = field(default_factory=list)

    @property
    def labels(self) -> list[str]:
        """One label per copy: ``index`` as given, else ``"0"``, ``"1"``, ..."""
        if self.index is not None:
            return list(self.index)
        return [str(i) for i in range(self.count)]

    @property
    def stride(self) -> int:
        """``increment`` once expansion has vouched for it.

        A template without a ``<dimIncrement>`` is never expanded, so every
        ``Dim`` the layout, the checks and the writers see has one.
        """
        assert self.increment is not None
        return self.increment


@dataclass
class Field:
    """A contiguous group of bits within a :class:`Register`.

    Attributes:
        name: Identifier of the field.
        bit_offset: Zero-based index of the field's least-significant bit.
        bit_width: Number of bits the field occupies.
        description: Optional human-readable description.
        access: Access policy. Raw (possibly ``None``) as parsed; filled in by
            the defaults resolution pass so every field carries a resolved value.
        enums: Enumerated values the field may take, if any.
        dim: Array shape when the field is one of several copies (SVD
            ``<dim>``, increment in bits); ``None`` for a single field. After
            expansion only a ``[%s]`` array keeps it, with ``name`` bare.
        expanded_from: The ``<dim>`` template this element was expanded from
            (``UART%s``), so a report can point at the one declaration behind
            several copies; ``None`` when written out by hand.
    """

    name: str
    bit_offset: int
    bit_width: int
    description: str | None = None
    access: Access | None = None
    enums: list[EnumeratedValue] = field(default_factory=list)
    dim: Dim | None = None
    expanded_from: str | None = None

    @property
    def mask(self) -> int:
        """The field's bit mask, shifted into position."""
        return ((1 << self.bit_width) - 1) << self.bit_offset


@dataclass
class Register:
    """A single addressable register within a :class:`Peripheral`.

    The ``size``, ``reset_value``, ``reset_mask``, and ``access`` fields hold
    the register's own declared value (``None`` when the source is silent).
    The defaults resolution pass then fills them from the inheritance chain, so
    every emitter sees fully-resolved values and never re-derives them.

    Attributes:
        name: Identifier of the register.
        address_offset: Offset from the owning peripheral's base, in address units.
        size: Width of the register in bits (resolved).
        reset_value: Value the register holds after reset (resolved; may be
            ``None`` if unspecified at every level).
        reset_mask: Which bits of ``reset_value`` are defined (resolved).
        description: Optional human-readable description.
        access: Access policy (resolved).
        fields: Bit fields defined within the register.
        dim: Array shape when the register is one of several copies (SVD
            ``<dim>``); ``None`` for a single register. After expansion only a
            ``[%s]`` array keeps it, and ``name`` is then the bare array name.
            Its stride is compared to the resolved ``size`` only after defaults
            resolution, in the checks and the layout, never here.
        expanded_from: The ``<dim>`` template this element was expanded from
            (``UART%s``), so a report can point at the one declaration behind
            several copies; ``None`` when written out by hand.
    """

    name: str
    address_offset: int
    size: int | None = None
    reset_value: int | None = None
    reset_mask: int | None = None
    description: str | None = None
    access: Access | None = None
    fields: list[Field] = field(default_factory=list)
    dim: Dim | None = None
    expanded_from: str | None = None


@dataclass
class Cluster:
    """A named group of registers within a :class:`Peripheral` (SVD ``<cluster>``).

    A cluster is a sub-block: its registers and nested clusters sit at offsets
    relative to the cluster's own ``address_offset``, and it is emitted as its
    own struct type used as one member of the enclosing struct -- or as an
    array of them when it carries a :class:`Dim` (DMA channels, timer capture
    units). The ``default_*`` fields are register-property defaults declared
    at cluster level, one rung between the peripheral and its registers.

    Attributes:
        name: Identifier of the cluster.
        address_offset: Offset from the enclosing peripheral or cluster, in
            address units.
        description: Optional human-readable description.
        header_struct_name: SVD ``headerStructName`` -- the vendor's name for
            the cluster's struct type; the cluster's own name when absent.
        derived_from: SVD ``derivedFrom`` (another cluster's name). Parsed and
            reported; not resolved yet.
        default_size: Cluster-level default register width in bits.
        default_access: Cluster-level default access policy.
        default_reset_value: Cluster-level default reset value.
        default_reset_mask: Cluster-level default reset mask.
        registers: Registers belonging to the cluster.
        clusters: Clusters nested inside this one.
        dim: Array shape when the cluster is one of several copies (SVD
            ``<dim>``); ``None`` for a single cluster. After expansion only a
            ``[%s]`` array keeps it, with ``name`` bare.
        expanded_from: The ``<dim>`` template this element was expanded from
            (``UART%s``), so a report can point at the one declaration behind
            several copies; ``None`` when written out by hand.
    """

    name: str
    address_offset: int
    description: str | None = None
    header_struct_name: str | None = None
    derived_from: str | None = None
    default_size: int | None = None
    default_access: Access | None = None
    default_reset_value: int | None = None
    default_reset_mask: int | None = None
    registers: list[Register] = field(default_factory=list)
    clusters: list[Cluster] = field(default_factory=list)
    dim: Dim | None = None
    expanded_from: str | None = None


#: The ``usage`` values CMSIS-SVD defines for an ``<addressBlock>``. A block that
#: omits ``usage`` holds registers: SVDConv's ``AddrBlockUsage`` and svd-rs both
#: model an undefined state that defaults to ``registers``, which regforge spells
#: ``None``. Named here so the layout and the writers share one vocabulary.
BLOCK_REGISTERS = "registers"
BLOCK_BUFFER = "buffer"
BLOCK_RESERVED = "reserved"


@dataclass
class AddressBlock:
    """A peripheral's declared memory footprint (SVD ``<addressBlock>``).

    A peripheral may declare several blocks (registers at one offset, a FIFO
    buffer window at another). The block is the vendor's contract for how much
    address space the peripheral occupies, and its ``usage`` decides what the
    C writer emits for it: a ``registers`` block defines the struct and its
    ``sizeof`` static-assert, a ``buffer`` block becomes one raw array member,
    and a ``reserved`` block becomes padding.

    Attributes:
        offset: Start of the block, in address units, relative to the base.
        size: Size of the block, in address units.
        usage: What the block holds -- ``"registers"``, ``"buffer"``, or
            ``"reserved"`` (``None`` when the source omits it).
    """

    offset: int
    size: int
    usage: str | None = None

    @property
    def holds_registers(self) -> bool:
        """Whether named registers live in this block (absent ``usage`` means yes)."""
        return self.usage in (None, BLOCK_REGISTERS)

    @property
    def is_buffer(self) -> bool:
        """Whether this block is a raw data window the vendor named no registers for."""
        return self.usage == BLOCK_BUFFER


@dataclass
class Interrupt:
    """An interrupt line a peripheral raises (SVD ``<interrupt>``).

    Attributes:
        name: Interrupt identifier, e.g. ``"UART0"`` or ``"TIM1_BRK_TIM9"``.
            Names the ``<name>_IRQn`` enumerator; may differ from the peripheral
            name and may be shared by several peripherals (one vector, many
            sources).
        value: Vector number (NVIC position); the enumerator's value.
        description: Optional human-readable description.
    """

    name: str
    value: int
    description: str | None = None


@dataclass
class Peripheral:
    """A peripheral block mapped at a base address.

    The ``default_*`` fields are register-property defaults declared at the
    peripheral level; the defaults resolution pass hands them down to registers
    that do not declare their own.

    Attributes:
        name: Identifier of the peripheral.
        base_address: Absolute base address of the peripheral.
        description: Optional human-readable description.
        derived_from: Name of the peripheral this one derives from (SVD
            ``derivedFrom``); the resolver copies that base's registers in.
        group_name: SVD ``groupName`` -- a family label (e.g. ``GPIO``);
            peripherals sharing it are candidates for one shared type.
        header_struct_name: SVD ``headerStructName`` -- the vendor's preferred
            name for the generated struct. Nordic ships it so generated types
            match their hand-written SDK; Cypress uses it where the instance
            name (``DW0``, ``CSD0``) would make a poor type name. It names the
            type only: grouping still follows ``derivedFrom``/``groupName``,
            since a shared name is not a claim about layout.
        default_size: Peripheral-level default register width in bits.
        default_access: Peripheral-level default access policy.
        default_reset_value: Peripheral-level default reset value.
        default_reset_mask: Peripheral-level default reset mask.
        registers: Registers belonging to the peripheral.
        interrupts: Interrupt lines the peripheral raises (SVD ``<interrupt>``).
        address_blocks: Declared memory footprint(s) (SVD ``<addressBlock>``).
        clusters: Register groups (SVD ``<cluster>``), each emitted as a nested
            struct member.
        dim: Array shape when the peripheral is a ``%s`` template for several
            copies (SVD ``<dim>``); cleared by expansion, which replaces the
            template with its copies.
        expanded_from: The ``<dim>`` template this element was expanded from
            (``UART%s``), so a report can point at the one declaration behind
            several copies; ``None`` when written out by hand.
    """

    name: str
    base_address: int
    description: str | None = None
    derived_from: str | None = None
    group_name: str | None = None
    header_struct_name: str | None = None
    default_size: int | None = None
    default_access: Access | None = None
    default_reset_value: int | None = None
    default_reset_mask: int | None = None
    registers: list[Register] = field(default_factory=list)
    interrupts: list[Interrupt] = field(default_factory=list)
    address_blocks: list[AddressBlock] = field(default_factory=list)
    clusters: list[Cluster] = field(default_factory=list)
    dim: Dim | None = None
    expanded_from: str | None = None


@dataclass
class Cpu:
    """The processor core a device is built around.

    Every field is optional: vendor descriptions routinely omit some, and
    several fields (``nvic_prio_bits``, ``vtor_present``, ``vendor_systick``)
    are specific to Arm Cortex-M cores. A reader for another architecture
    leaves the inapplicable fields ``None``; writers emit only what is present,
    never guessing at absent or suspect values.

    Attributes:
        name: Core identifier, e.g. ``"CM0PLUS"``.
        revision: Core revision, e.g. ``"r0p1"``.
        endian: Byte order, e.g. ``"little"`` or ``"big"``.
        mpu_present: Whether a memory protection unit is present.
        fpu_present: Whether a floating-point unit is present.
        vtor_present: Whether the vector table offset register is present.
        nvic_prio_bits: Implemented interrupt priority bits (Cortex-M).
        vendor_systick: Whether the vendor replaced the standard SysTick.
        num_interrupts: Number of device interrupt lines.
    """

    name: str | None = None
    revision: str | None = None
    endian: str | None = None
    mpu_present: bool | None = None
    fpu_present: bool | None = None
    vtor_present: bool | None = None
    nvic_prio_bits: int | None = None
    vendor_systick: bool | None = None
    num_interrupts: int | None = None


@dataclass
class Device:
    """A complete device and the peripherals it exposes.

    The identity fields (``vendor``, ``name``, ``series``, ``version``) come
    straight from the source description and are preserved so generated output
    can be traced back to the exact input it was produced from.

    Attributes:
        name: Identifier of the device.
        description: Optional human-readable description.
        vendor: Name of the silicon vendor, if given.
        series: Device family or series, if given.
        version: Version string of the source description, if given.
        license_text: License notice carried by the source description, if given.
        header_prefix: Vendor prefix for generated identifiers (SVD
            ``headerDefinitionsPrefix``); emitters prepend it to define names.
        vendor_extensions_xml: The raw ``<vendorExtensions>`` subtree, preserved
            verbatim as an opaque string for future interpreters. Never dropped.
        cpu: The processor core, if the source describes one.
        address_unit_bits: Bits selected by one address unit (8 for every
            byte-addressable device; the SVD default). All offsets, block sizes,
            and array strides in the IR are stored in these units, unconverted;
            converting to a target's native unit is the emitter's job.
        bus_width: Maximum data bus width in bits (SVD ``<width>``). The last
            fallback for a register's size, and the ceiling a register size is
            checked against.
        default_size: Device-level default register width in bits.
        default_access: Device-level default access policy.
        default_reset_value: Device-level default reset value.
        default_reset_mask: Device-level default reset mask.
        peripherals: Peripherals defined by the device.
    """

    name: str
    description: str | None = None
    vendor: str | None = None
    series: str | None = None
    version: str | None = None
    license_text: str | None = None
    header_prefix: str | None = None
    vendor_extensions_xml: str | None = None
    cpu: Cpu | None = None
    address_unit_bits: int = DEFAULT_ADDRESS_UNIT_BITS
    bus_width: int = DEFAULT_BUS_WIDTH
    default_size: int | None = None
    default_access: Access | None = None
    default_reset_value: int | None = None
    default_reset_mask: int | None = None
    peripherals: list[Peripheral] = field(default_factory=list)


def walk_clusters(clusters: list[Cluster], where: str) -> Iterator[tuple[str, Cluster]]:
    """Every cluster under ``clusters``, depth first, with its dotted path.

    ``where`` is the enclosing name (``"DMA"``); a nested cluster is reported
    as ``"DMA.CH.SUB"``. Shared by the passes, the checks and the writers so
    no two of them walk the tree differently.
    """
    for cluster in clusters:
        path = f"{where}.{cluster.name}"
        yield path, cluster
        yield from walk_clusters(cluster.clusters, path)

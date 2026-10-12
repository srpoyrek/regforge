"""A peripheral block mapped at a base address."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from regforge.ir.device.peripheral.registers_of import RegistersOf

if TYPE_CHECKING:
    from regforge.ir import (
        Access,
        AddressBlock,
        AlternateSet,
        Cluster,
        Dim,
        DimOrigin,
        Interrupt,
        Protection,
    )


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
        alternate_sets: The peripheral's registers, one :class:`AlternateSet` per word: a
            set of one view for a plain register, of several for registers that are
            different layouts of one word.
        registers: The same registers read flat, the views of every set in order. Passing
            ``registers=`` to the constructor, or assigning it, makes one set of one view
            per register; see :class:`RegistersOf`.
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
        default_protection: Peripheral-level default protection.
        origin: The array declaration this element was unrolled from, with its count,
            step and labels; ``None`` for an element written out by hand or kept whole.
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
    alternate_sets: list[AlternateSet] = field(default_factory=list)
    registers: RegistersOf = field(default=RegistersOf(), repr=False, compare=False)
    interrupts: list[Interrupt] = field(default_factory=list)
    address_blocks: list[AddressBlock] = field(default_factory=list)
    clusters: list[Cluster] = field(default_factory=list)
    dim: Dim | None = None
    expanded_from: str | None = None
    default_protection: Protection | None = None
    origin: DimOrigin | None = None

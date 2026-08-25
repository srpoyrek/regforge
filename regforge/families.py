"""Peripheral families: which peripherals share one emitted C type.

A family key is the ``derivedFrom`` chain root's ``groupName`` (else its name),
so peripherals linked by ``derivedFrom`` and peripherals merely sharing a
``groupName`` both collapse to one family. But we do not *trust* the members
match: ``groupName`` is a label, not a claim -- vendors apply it to genuinely
different silicon (STM32's advanced TIM1 has ``RCR``/``BDTR`` that general-purpose
TIM2..5 lack, all ``groupName=TIM``). So we structurally compare register layouts
and split divergent members into their own types.

When a group splits, the **largest** structurally-identical subgroup keeps the
plain family name; outliers get their own name -- matching how engineers already
talk ("the timers" vs "the advanced timer"). The split is recorded as a ``note``
on the kept family so the emitter can surface it. Reusable by the C writer, the
docs generator, diff mode, and the linter.
"""

from __future__ import annotations

from dataclasses import dataclass

from .ir import Device, Peripheral


@dataclass
class Family:
    """A group of peripherals that share one emitted C type.

    Attributes:
        name: the family/type name -- the root's ``groupName`` if it has one,
            otherwise the root peripheral's name.
        type_source: the peripheral whose registers define the shared type.
        instances: every peripheral emitted as an instance of that type.
        note: for the family a divergent group split into, a human-readable
            record of the split (which members went which way, first difference).
    """

    name: str
    type_source: Peripheral
    instances: tuple[Peripheral, ...]
    note: str | None = None


def _chain_root(peripheral: Peripheral, by_name: dict[str, Peripheral]) -> Peripheral:
    """The peripheral at the top of this one's ``derivedFrom`` chain."""
    seen: set[str] = set()
    current = peripheral
    while current.derived_from is not None and current.derived_from in by_name:
        if current.name in seen:  # cycle guard
            break
        seen.add(current.name)
        current = by_name[current.derived_from]
    return current


def _family_key(peripheral: Peripheral, by_name: dict[str, Peripheral]) -> str:
    """The family a peripheral belongs to: chain root's groupName, else its name."""
    root = _chain_root(peripheral, by_name)
    return root.group_name or root.name


def layout_signature(peripheral: Peripheral) -> tuple:
    """A hashable key for a peripheral's emitted struct shape.

    Two peripherals share a C type exactly when this matches: the same registers
    at the same offsets, sizes, and access (access drives the member's
    const-ness), *and* the same declared footprint. The blocks belong here
    because they shape the struct as surely as the registers do -- a ``buffer``
    block is a member, a ``reserved`` block is padding, and the ``registers``
    block sets the asserted size. Identical registers behind different blocks are
    different types, and merging them would size one from the other's footprint.
    """
    registers = tuple(
        (register.name, register.address_offset, register.size, register.access)
        for register in sorted(peripheral.registers, key=lambda r: r.address_offset)
    )
    blocks = tuple(
        (block.offset, block.size, block.usage)
        for block in sorted(peripheral.address_blocks, key=lambda b: (b.offset, b.size))
    )
    return (registers, blocks)


def first_divergence(left: tuple, right: tuple) -> str:
    """Name where two layout signatures first differ."""
    left_registers, left_blocks = left
    right_registers, right_blocks = right
    names_left = [entry[0] for entry in left_registers]
    names_right = [entry[0] for entry in right_registers]
    only_one_side = set(names_left) ^ set(names_right)
    if only_one_side:
        return sorted(only_one_side)[0]  # a register present on one side only
    for entry_left, entry_right in zip(left_registers, right_registers):
        if entry_left != entry_right:
            return entry_left[0]  # same name, differing offset/size/access
    if left_blocks != right_blocks:
        return "addressBlock"  # same registers, different declared footprint
    return "layout"


def group_families(device: Device) -> list[Family]:
    """Group peripherals into families that share one C type, verifying layout.

    Peripherals are grouped by family key; members are then bucketed by register
    layout. A single bucket is one clean family. Multiple buckets is a split: the
    largest bucket keeps the family name, outliers are named after themselves, and
    the kept family carries a ``note`` recording the split.
    """
    by_name = {peripheral.name: peripheral for peripheral in device.peripherals}

    groups: dict[str, list[Peripheral]] = {}
    for peripheral in device.peripherals:
        groups.setdefault(_family_key(peripheral, by_name), []).append(peripheral)

    families: list[Family] = []
    for key, members in groups.items():
        buckets: dict[tuple, list[Peripheral]] = {}
        for member in members:
            buckets.setdefault(layout_signature(member), []).append(member)

        if len(buckets) == 1:
            (bucket,) = buckets.values()
            source = next((m for m in bucket if m.derived_from is None), bucket[0])
            families.append(Family(name=key, type_source=source, instances=tuple(bucket)))
            continue

        # Divergent group: largest identical subgroup keeps the name (stable sort
        # keeps declaration order among equal-sized subgroups).
        subgroups = sorted(buckets.values(), key=len, reverse=True)
        summary = " | ".join(",".join(m.name for m in group) for group in subgroups)
        differ_at = first_divergence(
            layout_signature(subgroups[0][0]), layout_signature(subgroups[1][0])
        )
        note = (
            f"family {key}: split {len(subgroups)} ways by layout "
            f"({summary}); first differs at {differ_at}"
        )
        for index, group in enumerate(subgroups):
            source = next((m for m in group if m.derived_from is None), group[0])
            families.append(
                Family(
                    name=key if index == 0 else source.name,
                    type_source=source,
                    instances=tuple(group),
                    note=note if index == 0 else None,
                )
            )
    return families

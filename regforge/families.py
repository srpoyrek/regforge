"""Peripheral families: which peripherals share one emitted C type.

A family key is the ``derivedFrom`` chain root's ``groupName`` (else its name),
so peripherals linked by ``derivedFrom`` and peripherals merely sharing a
``groupName`` both collapse to one family. Within a family we do not *trust*
that the members match -- we structurally compare register layouts and split off
any member whose layout diverges, so the "one type, N instances" decision is
verified rather than assumed. Reusable by the C writer, the docs generator, diff
mode, and the linter.
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
        instances: every peripheral emitted as an instance of that type
            (includes ``type_source``), in declaration order.
    """

    name: str
    type_source: Peripheral
    instances: tuple[Peripheral, ...]


def _chain_root(peripheral: Peripheral, by_name: dict[str, Peripheral]) -> Peripheral:
    """The peripheral at the top of this one's ``derivedFrom`` chain."""
    seen: set[str] = set()
    current = peripheral
    while current.derived_from is not None and current.derived_from in by_name:
        if current.name in seen:  # cycle guard -- stop rather than loop forever
            break
        seen.add(current.name)
        current = by_name[current.derived_from]
    return current


def _family_key(peripheral: Peripheral, by_name: dict[str, Peripheral]) -> str:
    """The family a peripheral belongs to: chain root's groupName, else its name."""
    root = _chain_root(peripheral, by_name)
    return root.group_name or root.name


def _layout_signature(peripheral: Peripheral) -> tuple:
    """A hashable key for a peripheral's register layout.

    Two peripherals share a C type exactly when this matches: same registers at
    the same offsets, sizes, and access (access drives the member's const-ness).
    """
    return tuple(
        (register.name, register.address_offset, register.size, register.access)
        for register in sorted(peripheral.registers, key=lambda r: r.address_offset)
    )


def group_families(device: Device) -> list[Family]:
    """Group peripherals into families that share one C type, verifying layout.

    Peripherals are grouped by family key; within a group, members whose register
    layout matches the representative share one type, and any member with a
    divergent layout is split into its own single-instance family.
    """
    by_name = {peripheral.name: peripheral for peripheral in device.peripherals}

    # Group by family key, preserving declaration order.
    groups: dict[str, list[Peripheral]] = {}
    for peripheral in device.peripherals:
        groups.setdefault(_family_key(peripheral, by_name), []).append(peripheral)

    families: list[Family] = []
    for key, members in groups.items():
        # Representative for the shared type: the chain root if the group has one,
        # else the first member (a groupName group has no single root).
        source = next((m for m in members if m.derived_from is None), members[0])
        signature = _layout_signature(source)
        shared: list[Peripheral] = []
        divergent: list[Peripheral] = []
        for member in members:
            target = shared if _layout_signature(member) == signature else divergent
            target.append(member)

        families.append(Family(name=key, type_source=source, instances=tuple(shared)))
        # A divergent member gets its own type, named after itself (never the
        # group key -- two divergent members must not collide on one type name).
        for member in divergent:
            families.append(Family(name=member.name, type_source=member, instances=(member,)))
    return families

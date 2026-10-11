"""Where each register of a peripheral sits, with the clusters it is inside."""

from __future__ import annotations

from dataclasses import dataclass

from regforge.ir import Cluster, Peripheral, Register
from regforge.writers.html.wording import array_note


@dataclass(frozen=True)
class PlacedRegister:
    """A register together with where it sits in its peripheral.

    Attributes:
        register: The register.
        path: Its name with the clusters around it, ``CH.CTRL``.
        offset: Its distance from the peripheral's base, in address units.
        note: What the clusters around it are, when they are arrays; else ``None``.
    """

    register: Register
    path: str
    offset: int
    note: str | None


def placed_registers(peripheral: Peripheral) -> list[PlacedRegister]:
    """Every register of ``peripheral``, clusters walked, in the order they are declared."""
    placed: list[PlacedRegister] = []

    def visit(
        registers: list[Register],
        clusters: list[Cluster],
        prefix: str,
        base: int,
        note: str | None,
    ) -> None:
        for register in registers:
            placed.append(
                PlacedRegister(
                    register, prefix + register.name, base + register.address_offset, note
                )
            )
        for cluster in clusters:
            own = array_note(cluster, "units")
            joined = " -- ".join(n for n in (note, own) if n) or None
            visit(
                cluster.registers,
                cluster.clusters,
                prefix + cluster.name + ".",
                base + cluster.address_offset,
                joined,
            )

    visit(peripheral.registers, peripheral.clusters, "", 0, None)
    return placed

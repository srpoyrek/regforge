"""Where each register of a peripheral sits, with the clusters it is inside."""

from __future__ import annotations

from dataclasses import dataclass

from regforge.ir import AlternateSet, Cluster, Peripheral, Register
from regforge.writers.html.wording import array_note


@dataclass(frozen=True)
class PlacedRegister:
    """A register together with where it sits in its peripheral.

    Attributes:
        register: The register.
        path: Its name with the clusters around it, ``CH.CTRL``.
        offset: Its distance from the peripheral's base, in address units.
        note: What the clusters around it are, when they are arrays; else ``None``.
        alternates: The names of the other views of its word, when it shares it with any.
    """

    register: Register
    path: str
    offset: int
    note: str | None
    alternates: tuple[str, ...] = ()


def placed_registers(peripheral: Peripheral) -> list[PlacedRegister]:
    """Every register of ``peripheral``, clusters walked, in the order they are declared."""
    placed: list[PlacedRegister] = []

    def visit(
        sets: list[AlternateSet],
        clusters: list[Cluster],
        prefix: str,
        base: int,
        note: str | None,
    ) -> None:
        for alternate_set in sets:
            for register in alternate_set.views:
                others = tuple(n for n in alternate_set.names if n != register.name)
                placed.append(
                    PlacedRegister(
                        register,
                        prefix + register.name,
                        base + register.address_offset,
                        note,
                        others,
                    )
                )
        for cluster in clusters:
            own = array_note(cluster, "units")
            joined = " -- ".join(n for n in (note, own) if n) or None
            visit(
                cluster.alternate_sets,
                cluster.clusters,
                prefix + cluster.name + ".",
                base + cluster.address_offset,
                joined,
            )

    visit(peripheral.alternate_sets, peripheral.clusters, "", 0, None)
    return placed

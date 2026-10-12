"""A named group of registers within a peripheral."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from regforge.ir.device.peripheral.registers_of import RegistersOf

if TYPE_CHECKING:
    from regforge.ir import Access, AlternateSet, Dim, DimOrigin, Protection


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
        alternate_sets: The cluster's registers, one :class:`AlternateSet` per word: a
            set of one view for a plain register, of several for registers that are
            different layouts of one word.
        registers: The same registers read flat, the views of every set in order. Passing
            ``registers=`` to the constructor, or assigning it, makes one set of one view
            per register; see :class:`RegistersOf`.
        clusters: Clusters nested inside this one.
        dim: Array shape when the cluster is one of several copies (SVD
            ``<dim>``); ``None`` for a single cluster. After expansion only a
            ``[%s]`` array keeps it, with ``name`` bare.
        expanded_from: The ``<dim>`` template this element was expanded from
            (``UART%s``), so a report can point at the one declaration behind
            several copies; ``None`` when written out by hand.
        default_protection: Cluster-level default protection.
        origin: The array declaration this element was unrolled from, with its count,
            step and labels; ``None`` for an element written out by hand or kept whole.
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
    alternate_sets: list[AlternateSet] = field(default_factory=list)
    registers: RegistersOf = field(default=RegistersOf(), repr=False, compare=False)
    clusters: list[Cluster] = field(default_factory=list)
    dim: Dim | None = None
    expanded_from: str | None = None
    default_protection: Protection | None = None
    origin: DimOrigin | None = None


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

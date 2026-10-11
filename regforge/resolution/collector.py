"""The collector: builds what each resolution class needs, and gathers what they find.

Every resolution class knows only its own level and is handed plain data. This is the one
module that knows the whole device: it walks the registers, works out what each class
needs from the fields and registers it sees, and puts every class's findings in one list
for the command line to print.
"""

from __future__ import annotations

from collections.abc import Iterator

from regforge.finding import Finding
from regforge.ir import Device, Field, Peripheral, Register, walk_clusters
from regforge.ir.bit import claims
from regforge.resolution.bit import BitResolution


def _registers(peripheral: Peripheral) -> Iterator[tuple[str, Register]]:
    """Every register of ``peripheral``, clusters included, with its dotted path."""
    for register in peripheral.registers:
        yield f"{peripheral.name}.{register.name}", register
    for path, cluster in walk_clusters(peripheral.clusters, peripheral.name):
        for register in cluster.registers:
            yield f"{path}.{register.name}", register


def _label(field: Field) -> str:
    """The field's name, with its count when it is an array: ``OD[4]``."""
    return f"{field.name}[{field.dim.length}]" if field.dim is not None else field.name


def _copies_of_one_template(first: Field, second: Field) -> bool:
    """Whether both fields are copies expanded from the same ``<dim>`` template."""
    return first.expanded_from is not None and first.expanded_from == second.expanded_from


def _bits(field: Field, positions: list[int], where: str) -> list[BitResolution]:
    """The bits a field covers, as the bit class sees them: a position and a claimant."""
    label = _label(field)
    return [BitResolution(position, label, where) for position in sorted(positions)]


def _collisions(register: Register, size: int, where: str) -> list[Finding]:
    """Findings for the fields of ``register`` that share a bit, comparing their bits in pairs.

    This walk is a stand-in for the classes of the levels above the bit: the register will
    pick the pairs of fields and each field will hand the bit class its bits. Copies of one
    ``<dim>`` template are not compared with each other, since expansion has already
    reported them overlapping, and a field array overlapping itself is one field, which
    ``check_address_math`` reports.
    """
    positions: dict[int, list[int]] = {}
    for position, owners in claims(register).items():
        if position < size:  # a position past the width is not a bit of the register
            for owner in owners:
                positions.setdefault(id(owner), []).append(position)
    findings: list[Finding] = []
    fields = register.fields
    for index, first in enumerate(fields):
        first_positions = positions.get(id(first), [])
        for second in fields[index + 1 :]:
            second_positions = positions.get(id(second), [])
            if _copies_of_one_template(first, second):
                continue
            if not set(first_positions).intersection(second_positions):
                continue
            findings += BitResolution.compare_all(
                _bits(first, first_positions, where), _bits(second, second_positions, where)
            )
    return findings


def collect(device: Device) -> list[Finding]:
    """Everything the resolution classes find wrong in ``device``, in one list."""
    findings: list[Finding] = []
    for peripheral in device.peripherals:
        for where, register in _registers(peripheral):
            if register.size is None:
                continue  # without its width there are no bits to check
            findings += _collisions(register, register.size, where)
    return findings

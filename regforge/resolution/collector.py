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


def _claimants(register: Register) -> dict[int, list[str]]:
    """For each bit position, the labels of the fields that claim it.

    Two cases are not a collision of two fields, so each leaves the bit one claimant.
    Copies of one ``<dim>`` template overlapping each other count as the template alone,
    since expansion has already reported that; and a field array overlapping itself is
    one field (``check_address_math`` reports it).
    """
    found: dict[int, list[str]] = {}
    for position, owners in claims(register).items():
        template = owners[0].expanded_from
        if template is not None and all(owner.expanded_from == template for owner in owners):
            found[position] = [template]
        else:
            found[position] = [_label(owner) for owner in owners]
    return found


def collect(device: Device) -> list[Finding]:
    """Everything the resolution classes find wrong in ``device``, in one list."""
    findings: list[Finding] = []
    for peripheral in device.peripherals:
        for where, register in _registers(peripheral):
            if register.size is None:
                continue  # without its width there are no bits to check
            findings += BitResolution(register.size, _claimants(register), where).findings()
    return findings

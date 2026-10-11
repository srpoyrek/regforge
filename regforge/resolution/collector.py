"""The collector: builds what each resolution class needs, and gathers what they find.

Every resolution class knows only its own level and is handed plain data. This is the one
module that knows the whole device: it walks the registers, works out what each class
needs from the fields and registers it sees, and puts every class's findings in one list
for the command line to print.
"""

from __future__ import annotations

from collections.abc import Iterator

from regforge.finding import Finding
from regforge.ir import Device, Peripheral, Register, walk_clusters
from regforge.resolution.field import FieldResolution


def _registers(peripheral: Peripheral) -> Iterator[tuple[str, Register]]:
    """Every register of ``peripheral``, clusters included, with its dotted path."""
    for register in peripheral.registers:
        yield f"{peripheral.name}.{register.name}", register
    for path, cluster in walk_clusters(peripheral.clusters, peripheral.name):
        for register in cluster.registers:
            yield f"{path}.{register.name}", register


def _fields(register: Register, size: int, where: str) -> list[Finding]:
    """What the field class finds in the fields of ``register``.

    This walk stands in for the register's own class: the register will pick the pairs of
    fields to compare, and each field hands the bit class the bits it shares with the other.
    """
    fields = [FieldResolution(field, size, where) for field in register.fields]
    findings = FieldResolution.check_all(fields)
    for index, first in enumerate(fields):
        for second in fields[index + 1 :]:
            findings += first.compare(second)
    return findings


def collect(device: Device) -> list[Finding]:
    """Everything the resolution classes find wrong in ``device``, in one list."""
    findings: list[Finding] = []
    for peripheral in device.peripherals:
        for where, register in _registers(peripheral):
            if register.size is None:
                continue  # without its width there are no bits to check
            findings += _fields(register, register.size, where)
    return findings

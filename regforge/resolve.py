"""Resolution passes: expand ``dim`` templates, apply ``derivedFrom``, fill defaults.

Three passes turn the parsed IR into the flat, fully-valued device that every
downstream consumer -- each emitter, the docs generator, the linter -- reads,
so none of them re-derives a chain differently. They run in this order::

    parse -> expand_dim -> resolve_derived -> resolve_defaults -> checks -> emit

``expand_dim`` goes first so a ``derivedFrom`` can name a copy (``UART1`` out
of ``UART%s``), and so a derived peripheral that is itself a template is split
into shells before the base's registers are copied into each. ``resolve_derived``
precedes ``resolve_defaults`` so the copied registers resolve under the derived
peripheral's own chain (its ``<size>``/``<access>``, then the base's, then the
device's) instead of being frozen at the base's values.

``size``, ``access``, ``resetValue``, and ``resetMask`` may be declared at the
device, peripheral, cluster, register, or (for ``access``) field level, each
inheriting from the level above when silent. Vendors pick different levels --
nRF declares ``access`` at the register, RP2040 per field, STM32 leans on device
defaults -- so a parser that handles only one style produces wrong access
rights on the others.

Where ARM's SVDConv silently falls back to ``read-write`` when access is absent
at every level, the defaults pass makes the same choice (it is the only sane
default) but *warns*, so the fallback is visible and auditable.
"""

from __future__ import annotations

import copy
import re
from typing import NamedTuple, TypeVar

from .check import Finding, Severity
from .ir import Access, Cluster, Device, Dim, Field, Peripheral, Register, walk_clusters

_T = TypeVar("_T")

#: The placeholders SVD allows in a ``<dim>`` template's name: ``%s`` for
#: separately named copies, ``[%s]`` for an array kept as one element.
_COPY = "%s"
_ARRAY = "[%s]"
#: What a ``dimIndex`` label must look like to end up inside an identifier.
_IDENTIFIER_TAIL = re.compile(r"[A-Za-z0-9_]+")


def _first(*values: _T | None) -> _T | None:
    """Return the first value that is not ``None`` (``None`` if all are)."""
    for value in values:
        if value is not None:
            return value
    return None


# --- dim expansion ---


def _stem(pattern: str) -> str:
    """The name pattern without its placeholder: ``UART%s`` -> ``UART``, ``PORT_%s`` -> ``PORT``."""
    return pattern.replace(_ARRAY, "").replace(_COPY, "").strip("_")


def _keep_as_array(
    element: Register | Cluster | Field, where: str, findings: list[Finding]
) -> None:
    """Drop ``[%s]`` from an element's name and keep its ``dim`` as the array shape.

    Array elements are indexed ``0..count-1`` by the language, not by labels, so
    a ``dimIndex`` on an array has nothing to name; it is reported and cleared.
    A cluster array's type takes ``dimName`` when it has no ``headerStructName``.
    """
    assert element.dim is not None
    element.name = element.name.replace(_ARRAY, "")
    element.dim.array = True
    if element.dim.index is not None:
        findings.append(
            Finding(
                Severity.WARNING,
                f"{where}.{element.name}[%s]: dimIndex ignored -- array elements are "
                f"indexed 0..{element.dim.count - 1} by the language, not by labels",
            )
        )
        element.dim.index = None
    if isinstance(element, Cluster) and not element.header_struct_name:
        element.header_struct_name = element.dim.name


def _labels(dim: Dim, where: str, findings: list[Finding]) -> list[str]:
    """The label for each copy, made usable: counted by ``dim``, identifier-clean, distinct.

    ``dim`` is trusted for the count: missing labels take their index, extra
    ones are dropped. A label that is not an identifier tail is rewritten with
    underscores, or falls back to its index when nothing is left. Labels that
    repeat would name two copies alike, which no header can hold, so the whole
    list falls back to ``0..count-1``; that one is an error, the rest warnings.
    """
    if dim.index is None:
        return [str(i) for i in range(dim.count)]
    labels = list(dim.index)
    if len(labels) != dim.count:
        fix = (
            "missing labels take their index" if len(labels) < dim.count else "extra labels dropped"
        )
        findings.append(
            Finding(
                Severity.WARNING,
                f"{where}: dimIndex gives {len(labels)} label(s) for <dim> {dim.count} "
                f"-- trusting <dim>: {fix}",
            )
        )
        labels = labels[: dim.count] + [str(i) for i in range(len(labels), dim.count)]
    for position, label in enumerate(labels):
        if not _IDENTIFIER_TAIL.fullmatch(label):
            cleaned = re.sub(r"[^A-Za-z0-9_]", "_", label).strip("_") or str(position)
            findings.append(
                Finding(
                    Severity.WARNING,
                    f"{where}: dimIndex label '{label}' is not an identifier -- using '{cleaned}'",
                )
            )
            labels[position] = cleaned
    if len(set(labels)) != len(labels):
        findings.append(
            Finding(
                Severity.ERROR,
                f"{where}: dimIndex labels repeat ({','.join(labels)}) -- two copies cannot "
                f"share a name; falling back to 0..{dim.count - 1}",
            )
        )
        labels = [str(i) for i in range(dim.count)]
    return labels


def _pattern(name: str, labels: list[str], where: str, findings: list[Finding]) -> str:
    """The name with its placeholder: appended when missing, reported when repeated.

    ``<dim>`` on a plain name would make every copy the same identifier, a C
    redefinition, so the index (or label) goes on the end and the file is told
    where it can say otherwise. The spec allows one ``%s``; a name with several
    gets the same label in every one, which is what a reader would expect, and
    is reported so the author can check that is what was meant.
    """
    if _COPY not in name:
        findings.append(
            Finding(
                Severity.WARNING,
                f"{where}: <dim> on a name without a %s placeholder -- copies are named "
                f"{name}{labels[0]}..{name}{labels[-1]} (index appended) so the header "
                "compiles; put %s in the name to choose where it goes",
            )
        )
        return name + _COPY
    if name.count(_COPY) > 1:
        findings.append(
            Finding(
                Severity.WARNING,
                f"{where}: name has {name.count(_COPY)} %s placeholders (the spec allows one) "
                f"-- every occurrence takes the same label ({name.replace(_COPY, labels[0])})",
            )
        )
    return name


def _expand_fields(register: Register, where: str, findings: list[Finding]) -> None:
    """Expand the ``%s`` fields of ``register`` in place; the increment is in bits."""
    expanded: list[Field] = []
    for field_ in register.fields:
        if field_.dim is None or field_.dim.array:
            expanded.append(field_)
        elif _ARRAY in field_.name:
            _keep_as_array(field_, where, findings)
            expanded.append(field_)
        else:
            path = f"{where}.{field_.name}"
            labels = _labels(field_.dim, path, findings)
            pattern = _pattern(field_.name, labels, path, findings)
            for index, label in enumerate(labels):
                clone = copy.deepcopy(field_)
                clone.dim = None
                clone.name = pattern.replace(_COPY, label)
                clone.bit_offset = field_.bit_offset + index * field_.dim.increment
                expanded.append(clone)
    register.fields = expanded


def _expand_registers(
    registers: list[Register], where: str, findings: list[Finding]
) -> list[Register]:
    """The register list with every ``%s`` template replaced by its copies, in place."""
    expanded: list[Register] = []
    for register in registers:
        # Fields first, on the template, so every copy carries the expanded set.
        _expand_fields(register, f"{where}.{register.name}", findings)
        if register.dim is None or register.dim.array:
            expanded.append(register)
        elif _ARRAY in register.name:
            _keep_as_array(register, where, findings)
            expanded.append(register)
        else:
            path = f"{where}.{register.name}"
            labels = _labels(register.dim, path, findings)
            pattern = _pattern(register.name, labels, path, findings)
            for index, label in enumerate(labels):
                clone = copy.deepcopy(register)
                clone.dim = None
                clone.name = pattern.replace(_COPY, label)
                clone.address_offset = register.address_offset + index * register.dim.increment
                expanded.append(clone)
    return expanded


def _expand_clusters(clusters: list[Cluster], where: str, findings: list[Finding]) -> list[Cluster]:
    """The cluster list with every ``%s`` template replaced by its copies, recursively."""
    expanded: list[Cluster] = []
    for cluster in clusters:
        path = f"{where}.{cluster.name}"
        cluster.registers = _expand_registers(cluster.registers, path, findings)
        cluster.clusters = _expand_clusters(cluster.clusters, path, findings)
        if cluster.dim is None or cluster.dim.array:
            expanded.append(cluster)
        elif _ARRAY in cluster.name:
            _keep_as_array(cluster, where, findings)
            expanded.append(cluster)
        else:
            labels = _labels(cluster.dim, path, findings)
            pattern = _pattern(cluster.name, labels, path, findings)
            # The copies share one struct type: the vendor's headerStructName,
            # else its dimName, else the pattern's stem.
            type_name = cluster.header_struct_name or cluster.dim.name or _stem(pattern)
            for index, label in enumerate(labels):
                clone = copy.deepcopy(cluster)
                clone.dim = None
                clone.name = pattern.replace(_COPY, label)
                clone.address_offset = cluster.address_offset + index * cluster.dim.increment
                clone.header_struct_name = type_name
                expanded.append(clone)
    return expanded


def expand_dim(device: Device) -> list[Finding]:
    """Expand every ``<dim>`` template into its copies, in place.

    Runs first, straight after parsing, so a later ``derivedFrom`` can name a
    copy and a derived peripheral that is itself a template is split before the
    base's registers are copied into each shell.

    A ``NAME%s`` template becomes ``count`` copies, each renamed with one label
    and moved ``increment`` along -- address units for a peripheral, cluster or
    register, bits for a field -- replacing the template at its position. A
    ``NAME[%s]`` register, cluster or field is an array: it stays one element,
    with the brackets dropped from its name and ``dim`` kept for the layout and
    the writers. A peripheral is an instance, not an array (``UART[0]`` is not
    an identifier), so ``[%s]`` on one is treated as ``%s`` and reported. A
    template whose name has no ``%s`` at all gets the index appended (``UART``
    becomes ``UART0``..) and is reported too: identical copies would collide.

    Labels come from ``dimIndex``, made usable first (see :func:`_labels`):
    counted by ``dim``, cleaned to identifier tails, and distinct -- repeated
    labels are the one error here, since two copies cannot share a name.

    Peripheral copies form one family: the pattern's stem (``UART`` from
    ``UART%s``) stands in for a missing ``groupName``, and ``dimName`` names
    the type when no ``headerStructName`` does, so one type is emitted with
    ``count`` instances. Interrupts are copied to every instance -- the
    template declares them for each -- with ``%s`` substituted in their names;
    ``<dim>`` cannot shift a vector number, so the copies share it, and that is
    reported.

    Nothing here looks at sizes or strides: a register may still lack its
    ``size`` (it comes from the device ``<width>`` in defaults resolution), so
    whether a stride fits is left to the checks and the layout, which run later.
    Mutates ``device`` in place and returns findings, warnings and errors.
    """
    findings: list[Finding] = []
    expanded: list[Peripheral] = []
    for peripheral in device.peripherals:
        peripheral.registers = _expand_registers(peripheral.registers, peripheral.name, findings)
        peripheral.clusters = _expand_clusters(peripheral.clusters, peripheral.name, findings)
        if peripheral.dim is None or peripheral.dim.array:
            expanded.append(peripheral)
            continue
        pattern = peripheral.name
        if _ARRAY in pattern:
            findings.append(
                Finding(
                    Severity.WARNING,
                    f"{pattern}: a peripheral is an instance, not an array -- emitted as "
                    f"{peripheral.dim.count} separately named instances",
                )
            )
            pattern = pattern.replace(_ARRAY, _COPY)
        labels = _labels(peripheral.dim, peripheral.name, findings)
        pattern = _pattern(pattern, labels, peripheral.name, findings)
        if peripheral.interrupts:
            vectors = ", ".join(str(interrupt.value) for interrupt in peripheral.interrupts)
            findings.append(
                Finding(
                    Severity.WARNING,
                    f"{pattern}: its interrupt(s) (vector {vectors}) are copied to all "
                    f"{peripheral.dim.count} instances -- <dim> cannot shift a vector number, "
                    "so they share it; declare the instances separately if each has its own",
                )
            )
        stem = _stem(pattern)
        for index, label in enumerate(labels):
            clone = copy.deepcopy(peripheral)
            clone.dim = None
            clone.name = pattern.replace(_COPY, label)
            clone.base_address = peripheral.base_address + index * peripheral.dim.increment
            # dimName names the type below headerStructName and above groupName;
            # giving it the headerStructName slot is exactly that precedence.
            if not clone.header_struct_name:
                clone.header_struct_name = peripheral.dim.name
            if not clone.group_name:
                clone.group_name = stem
            for interrupt in clone.interrupts:
                interrupt.name = interrupt.name.replace(_COPY, label)
            expanded.append(clone)
    device.peripherals = expanded
    return findings


# --- derivedFrom resolution ---


def resolve_derived(device: Device) -> list[str]:
    """Copy each derived peripheral's base into it, before defaults resolution.

    A peripheral with ``derived_from`` inherits the registers, clusters and
    address blocks of the peripheral it names, at its own base address, plus
    the base's ``headerStructName`` and peripheral-level defaults wherever it
    declares none of its own -- so its copies resolve exactly as the base's
    registers would, unless it overrides a default, in which case the override
    wins. The base is resolved first so ``derivedFrom`` chains inherit a
    complete set. Mutates ``device`` in place and returns warnings: an unknown
    base, a cycle, or a cluster ``derivedFrom``, which is not resolved yet.
    """
    warnings: list[str] = []
    by_name = {peripheral.name: peripheral for peripheral in device.peripherals}
    resolving: set[str] = set()

    def ensure(peripheral: Peripheral) -> None:
        if peripheral.derived_from is None or peripheral.registers or peripheral.clusters:
            return
        base = by_name.get(peripheral.derived_from)
        if base is None:
            warnings.append(
                f"{peripheral.name}: derivedFrom '{peripheral.derived_from}' -- "
                "no such peripheral; left empty"
            )
            return
        if peripheral.name in resolving:
            warnings.append(f"{peripheral.name}: derivedFrom cycle -- left empty")
            return
        resolving.add(peripheral.name)
        ensure(base)  # resolve the base first, so chains inherit a full set
        resolving.discard(peripheral.name)
        # Registers and clusters are inherited; interrupts are NOT. An interrupt
        # is per-instance (each peripheral has its own vector), so a derived
        # peripheral uses only its own <interrupt>. Inheriting the base's
        # verbatim would put two peripherals on one vector under the base's
        # name -- almost always a bug, surfaced by check_derived_interrupts().
        peripheral.registers = [copy.deepcopy(register) for register in base.registers]
        peripheral.clusters = [copy.deepcopy(cluster) for cluster in base.clusters]
        # The addressBlock IS inherited: the footprint (offset/size relative to
        # the base) is identical for every instance of a type.
        if not peripheral.address_blocks:
            peripheral.address_blocks = [copy.deepcopy(block) for block in base.address_blocks]
        # headerStructName is inherited too: it names the shared type, and nRF
        # relies on this -- only SPIM0 carries it, SPIM1/SPIM2 derive from it.
        if peripheral.header_struct_name is None:
            peripheral.header_struct_name = base.header_struct_name
        # So are the peripheral-level defaults, where the derived one is silent:
        # this pass runs before defaults resolution, and the copied registers
        # must resolve as the base's do unless the derived peripheral overrides.
        if peripheral.default_size is None:
            peripheral.default_size = base.default_size
        if peripheral.default_access is None:
            peripheral.default_access = base.default_access
        if peripheral.default_reset_value is None:
            peripheral.default_reset_value = base.default_reset_value
        if peripheral.default_reset_mask is None:
            peripheral.default_reset_mask = base.default_reset_mask

    for peripheral in device.peripherals:
        ensure(peripheral)
        for path, cluster in walk_clusters(peripheral.clusters, peripheral.name):
            if cluster.derived_from is not None:
                warnings.append(
                    f"{path}: derivedFrom '{cluster.derived_from}' on a cluster is not "
                    "resolved yet -- the cluster is emitted as written"
                )
    return warnings


# --- defaults resolution ---


class _Defaults(NamedTuple):
    """The register-property values one level hands down to the next."""

    size: int | None
    access: Access | None
    reset_value: int | None
    reset_mask: int | None


def _narrow(
    size: int | None,
    access: Access | None,
    reset_value: int | None,
    reset_mask: int | None,
    inherited: _Defaults,
) -> _Defaults:
    """One level's own declarations over what it inherits."""
    return _Defaults(
        _first(size, inherited.size),
        _first(access, inherited.access),
        _first(reset_value, inherited.reset_value),
        _first(reset_mask, inherited.reset_mask),
    )


def _resolve_registers(
    registers: list[Register], where: str, inherited: _Defaults, warnings: list[str]
) -> None:
    for register in registers:
        register.size = _first(register.size, inherited.size)
        register.reset_value = _first(register.reset_value, inherited.reset_value)
        register.reset_mask = _first(register.reset_mask, inherited.reset_mask)

        access = _first(register.access, inherited.access)
        if access is None:
            access = Access.READ_WRITE
            warnings.append(
                f"{where}.{register.name}: access unspecified at every "
                "level -- defaulting to read-write (unverified)"
            )
        register.access = access

        for field_ in register.fields:
            field_.access = _first(field_.access, register.access)


def _resolve_clusters(
    clusters: list[Cluster], where: str, inherited: _Defaults, warnings: list[str]
) -> None:
    for cluster in clusters:
        own = _narrow(
            cluster.default_size,
            cluster.default_access,
            cluster.default_reset_value,
            cluster.default_reset_mask,
            inherited,
        )
        path = f"{where}.{cluster.name}"
        _resolve_registers(cluster.registers, path, own, warnings)
        _resolve_clusters(cluster.clusters, path, own, warnings)


def resolve_defaults(device: Device) -> list[str]:
    """Fill inherited size/access/reset values into every register and field.

    The chain is device -> peripheral -> cluster (each nested cluster adds a
    rung) -> register -> field. Mutates ``device`` in place and returns
    human-readable warnings -- one per register whose access is unspecified at
    every level and falls back to read-write.
    """
    warnings: list[str] = []
    device_defaults = _Defaults(
        _first(device.default_size, device.bus_width),
        device.default_access,
        device.default_reset_value,
        device.default_reset_mask,
    )
    for peripheral in device.peripherals:
        own = _narrow(
            peripheral.default_size,
            peripheral.default_access,
            peripheral.default_reset_value,
            peripheral.default_reset_mask,
            device_defaults,
        )
        _resolve_registers(peripheral.registers, peripheral.name, own, warnings)
        _resolve_clusters(peripheral.clusters, peripheral.name, own, warnings)
    return warnings

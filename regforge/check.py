"""Static consistency checks over the IR (the core of ``regforge check``).

These checks read only parsed IR fields, so they run the moment a device
loads -- no emitter, target, or external tool involved. Findings are advisory
(:attr:`Severity.WARNING`) unless they encode an internal contradiction that
no real hardware could satisfy (:attr:`Severity.ERROR`): a bus that cannot
address a whole unit is impossible; a register wider than the bus is merely
unusual (a multi-access register), so a human decides.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum

from .families import first_divergence, layout_signature
from .ir import Cluster, Device, Peripheral, Register
from .layout import (
    LayoutError,
    cluster_element_units,
    cluster_span_units,
    peripheral_layout,
    register_span_units,
    registers_end,
    units_to_bytes,
)


class Severity(Enum):
    """How seriously to treat a :class:`Finding`."""

    WARNING = "warning"
    ERROR = "error"


@dataclass
class Finding:
    """A single consistency issue discovered in a device."""

    severity: Severity
    message: str


def _is_power_of_two(value: int) -> bool:
    """True for 8, 16, 32, 64, 128, ... -- any valid bit width, now or future.

    Bus and address-unit widths are always powers of two; a non-power (7, 24,
    33) signals a typo. Testing the property instead of a hardcoded list keeps
    the check correct as wider buses appear, without editing this file.
    """
    return value > 0 and (value & (value - 1)) == 0


def _clusters_with_offsets(
    clusters: list[Cluster], where: str, base: int
) -> Iterator[tuple[str, Cluster, int]]:
    """Every cluster, depth first, with its dotted path and its offset from the peripheral."""
    for cluster in clusters:
        path = f"{where}.{cluster.name}"
        offset = base + cluster.address_offset
        yield path, cluster, offset
        yield from _clusters_with_offsets(cluster.clusters, path, offset)


def _registers_with_offsets(peripheral: Peripheral) -> Iterator[tuple[str, int, Register]]:
    """Every register of ``peripheral``, clusters included, with its path and offset.

    The offset is from the peripheral base, in address units; a register inside
    an array cluster is reported at its first element's position.
    """
    for register in peripheral.registers:
        yield f"{peripheral.name}.{register.name}", register.address_offset, register
    for path, cluster, base in _clusters_with_offsets(peripheral.clusters, peripheral.name, 0):
        for register in cluster.registers:
            yield f"{path}.{register.name}", base + register.address_offset, register


def check_address_math(device: Device) -> list[Finding]:
    """Check that address units, bus width, register sizes and array strides agree.

    The pair ``(address_unit_bits, bus_width)`` defines the device's address
    math; every register's size and offset must be consistent with it, and an
    array's stride must at least cover one element -- a register, cluster or
    field array whose elements overlap is a contradiction no hardware can
    satisfy (``ERROR``). Registers inside clusters are checked at their offset
    from the peripheral. Strides are compared only once sizes are resolved.
    """
    findings: list[Finding] = []
    unit_bits = device.address_unit_bits
    bus_width = device.bus_width

    if not _is_power_of_two(unit_bits):
        findings.append(
            Finding(
                Severity.WARNING,
                f"addressUnitBits={unit_bits} is not a power of two "
                "-- likely a vendor-file typo",
            )
        )
    if bus_width < unit_bits:
        findings.append(
            Finding(
                Severity.ERROR,
                f"width={bus_width} < addressUnitBits={unit_bits}: "
                "the bus is narrower than a single address unit",
            )
        )
    elif bus_width % unit_bits != 0:
        findings.append(
            Finding(
                Severity.ERROR,
                f"width={bus_width} is not a multiple of addressUnitBits={unit_bits}: "
                "the bus cannot make whole-unit accesses",
            )
        )

    for peripheral in device.peripherals:
        for path, cluster, _ in _clusters_with_offsets(peripheral.clusters, peripheral.name, 0):
            if cluster.dim is None:
                continue
            contents = cluster_element_units(cluster, unit_bits)
            if cluster.dim.increment < contents:
                findings.append(
                    Finding(
                        Severity.ERROR,
                        f"{path}[{cluster.dim.count}]: stride {cluster.dim.increment} address "
                        f"unit(s) is smaller than the cluster's contents ({contents}) -- "
                        "the array's elements overlap",
                    )
                )
        for name, offset, register in _registers_with_offsets(peripheral):
            for field_ in register.fields:
                if field_.dim is not None and field_.dim.increment < field_.bit_width:
                    findings.append(
                        Finding(
                            Severity.ERROR,
                            f"{name}.{field_.name}[{field_.dim.count}]: increment "
                            f"{field_.dim.increment} bit(s) is smaller than the "
                            f"{field_.bit_width}-bit field -- the array's elements overlap",
                        )
                    )
            if register.size is None:
                continue  # size checks need a resolved size; nothing to check here
            if register.size > bus_width:
                findings.append(
                    Finding(
                        Severity.WARNING,
                        f"{name}: register size {register.size} > bus width {bus_width} "
                        "-- a multi-access register, or a vendor error",
                    )
                )
            if register.size % unit_bits != 0:
                findings.append(
                    Finding(
                        Severity.WARNING,
                        f"{name}: register size {register.size} is not a whole number "
                        f"of address units ({unit_bits})",
                    )
                )
            units_per_register = register.size // unit_bits
            if units_per_register and offset % units_per_register != 0:
                findings.append(
                    Finding(
                        Severity.WARNING,
                        f"{name}: offset {offset:#x} is misaligned "
                        f"for a {register.size}-bit register",
                    )
                )
            if register.dim is not None and register.dim.increment < units_per_register:
                findings.append(
                    Finding(
                        Severity.ERROR,
                        f"{name}[{register.dim.count}]: stride {register.dim.increment} "
                        f"address unit(s) is smaller than the {register.size}-bit element "
                        "-- the array's elements overlap",
                    )
                )
    return findings


def check_derived_chains(device: Device) -> list[Finding]:
    """Flag ``derivedFrom`` chains deeper than one level.

    A chain (A derives from B derives from C) is legal but rare, and handled
    inconsistently by other SVD tools -- a portability hazard worth surfacing.
    Depth 1 (the common ``UART1 derivedFrom UART0``) is fine.
    """
    findings: list[Finding] = []
    by_name = {peripheral.name: peripheral for peripheral in device.peripherals}
    for peripheral in device.peripherals:
        depth = 0
        seen: set[str] = set()
        current = peripheral
        while current.derived_from is not None and current.derived_from in by_name:
            if current.name in seen:  # cycle guard
                break
            seen.add(current.name)
            current = by_name[current.derived_from]
            depth += 1
        if depth > 1:
            findings.append(
                Finding(
                    Severity.WARNING,
                    f"{peripheral.name}: derivedFrom chain is {depth} levels deep -- "
                    "legal but bug-prone in some SVD tools (portability hazard)",
                )
            )
    return findings


def check_derived_interrupts(device: Device) -> list[Finding]:
    """Flag interrupt mistakes on ``derivedFrom`` peripherals.

    An interrupt is per-instance: a derived peripheral shares its base's register
    layout but has its own vector, so regforge does not inherit ``<interrupt>``
    across ``derivedFrom`` (see :func:`regforge.resolve.resolve_derived`). Two
    vendor-file bugs follow, both of which stock tooling accepts silently:

    * **omission** -- the derived peripheral declares no interrupt while its base
      has one. Per the SVD spec it would silently inherit the base's vector (two
      peripherals, one vector, undeclared); regforge does not, so the derived
      peripheral ends up with no vector at all.
    * **copy-paste** -- the derived peripheral declares an interrupt whose value
      equals the base's. A distinct instance almost always needs its own vector.
    """
    findings: list[Finding] = []
    by_name = {peripheral.name: peripheral for peripheral in device.peripherals}
    for peripheral in device.peripherals:
        if peripheral.derived_from is None:
            continue
        base = by_name.get(peripheral.derived_from)
        if base is None or not base.interrupts:
            continue
        if not peripheral.interrupts:
            vectors = ", ".join(str(interrupt.value) for interrupt in base.interrupts)
            findings.append(
                Finding(
                    Severity.WARNING,
                    f"{peripheral.name}: derivedFrom '{base.name}' but declares no "
                    f"interrupt of its own; per SVD spec it would inherit the base's "
                    f"vector(s) ({vectors}) -- two peripherals on one vector. regforge "
                    f"treats interrupts as per-instance and does not inherit, so "
                    f"{peripheral.name} has no vector; declare its own <interrupt>.",
                )
            )
            continue
        base_values = {interrupt.value for interrupt in base.interrupts}
        for interrupt in peripheral.interrupts:
            if interrupt.value in base_values:
                findings.append(
                    Finding(
                        Severity.WARNING,
                        f"{peripheral.name}: interrupt '{interrupt.name}' uses vector "
                        f"{interrupt.value}, identical to its base '{base.name}' -- a "
                        f"derived instance almost always needs its own vector "
                        f"(likely a copy-paste).",
                    )
                )
    return findings


def check_group_divergence(device: Device) -> list[Finding]:
    """Warn when a ``groupName`` covers peripherals with different layouts.

    ``groupName`` is a label, not a structural claim: vendors apply one name to
    genuinely different silicon (STM32's advanced vs general-purpose timers).
    Trusting it as a single type is how ``TIM2->BDTR`` compiles against a
    reserved address in stock headers. Flagging divergence is the evidence that a
    vendor's family labels cannot be trusted unverified.
    """
    findings: list[Finding] = []
    groups: dict[str, list] = {}
    for peripheral in device.peripherals:
        if peripheral.group_name:
            groups.setdefault(peripheral.group_name, []).append(peripheral)
    for group, members in groups.items():
        by_signature: dict[tuple, list] = {}
        for member in members:
            by_signature.setdefault(layout_signature(member), []).append(member)
        if len(by_signature) > 1:
            signatures = list(by_signature)
            register = first_divergence(signatures[0], signatures[1])
            findings.append(
                Finding(
                    Severity.WARNING,
                    f"groupName '{group}': members have differing layouts "
                    f"(first differs at {register}) -- the label is not one verified "
                    "type; regforge emits separate types",
                )
            )
    return findings


#: Uncovered padding, in bytes, tolerated inside a peripheral before it is
#: reported. Two bytes absorbs the sub-word alignment holes vendors leave
#: constantly (the median gap across a 2,499-gap survey is 2 bytes) while still
#: naming anything the peripheral pads over without having claimed it.
MAX_UNOWNED_GAP_BYTES = 2


def check_unowned_gaps(device: Device) -> list[Finding]:
    """Flag padding a peripheral emits over space no ``addressBlock`` claims.

    A C struct cannot have holes, so the space between two registers becomes
    RESERVED padding. That is honest while some block covers the range -- the
    vendor declared the peripheral owns it, and a sifive PLIC really does span
    64 MB. Where no block covers it, regforge is inventing a claim: esp32's UART
    puts ``TX_FIFO`` 0x200C0000 past its register window, and the emitted struct
    grows a 537 MB reserved array that nothing in the source declares.

    The padding is still emitted -- the offsets it produces are correct, and
    splitting the peripheral would deny a footprint the vendor may simply have
    described badly. This says so rather than passing it off as a real layout.
    """
    findings: list[Finding] = []
    unit_bits = device.address_unit_bits
    for peripheral in device.peripherals:
        spans = sorted(
            (
                units_to_bytes(block.offset, unit_bits),
                units_to_bytes(block.offset + block.size, unit_bits),
            )
            for block in peripheral.address_blocks
        )
        try:
            slots = peripheral_layout(peripheral, unit_bits)
        except LayoutError:
            continue  # overlapping registers: a different check's story
        for slot in slots:
            if not slot.is_reserved:
                continue
            uncovered = _uncovered_bytes(slot.offset, slot.offset + slot.gap_bytes, spans)
            if uncovered > MAX_UNOWNED_GAP_BYTES:
                findings.append(
                    Finding(
                        Severity.WARNING,
                        f"{peripheral.name}: [{slot.offset:#x}, "
                        f"{slot.offset + slot.gap_bytes:#x}) is padded into the struct "
                        f"but {uncovered} byte(s) of it lie outside every declared "
                        "addressBlock -- the peripheral never claimed that space",
                    )
                )
    return findings


def _uncovered_bytes(start: int, end: int, spans: list[tuple[int, int]]) -> int:
    """Bytes of ``[start, end)`` that no span in ``spans`` covers.

    ``spans`` must be sorted by start. Walks a cursor forward through the
    overlapping-or-not block ranges, accumulating whatever they skip over.
    """
    uncovered = 0
    cursor = start
    for span_start, span_end in spans:
        if span_start > cursor:
            uncovered += min(span_start, end) - cursor
        cursor = max(cursor, span_end)
        if cursor >= end:
            return uncovered
    return uncovered + (end - cursor)


def check_address_blocks(device: Device) -> list[Finding]:
    """Check a peripheral's registers lie within its declared ``registers``
    addressBlock(s), and that a peripheral's own blocks do not overlap.

    ``addressBlock`` is the vendor's footprint contract; CMSIS discards it. A
    register beyond the block means the block under-declares the peripheral, and
    two blocks of one peripheral overlapping is a self-contradiction -- both are
    real vendor-file bugs, surfaced here (advisory ``WARNING``). An array is
    measured to its last element, and a cluster as one extent covering its
    every member and element.
    """
    findings: list[Finding] = []
    unit_bits = device.address_unit_bits
    for peripheral in device.peripherals:
        blocks = peripheral.address_blocks
        registers_blocks = [b for b in blocks if b.usage in (None, "registers")]
        extents = [
            (register.name, register.address_offset, register_span_units(register, unit_bits))
            for register in peripheral.registers
        ] + [
            (cluster.name, cluster.address_offset, cluster_span_units(cluster, unit_bits))
            for cluster in peripheral.clusters
        ]
        for name, start, span in extents:
            if not registers_blocks:
                continue
            end = start + span
            if not any(b.offset <= start and end <= b.offset + b.size for b in registers_blocks):
                findings.append(
                    Finding(
                        Severity.WARNING,
                        f"{peripheral.name}.{name}: at offset {start:#x} lies "
                        "outside the peripheral's registers addressBlock(s) -- the block "
                        "under-declares the footprint",
                    )
                )
        for i in range(len(blocks)):
            for j in range(i + 1, len(blocks)):
                first, second = blocks[i], blocks[j]
                if first.offset < second.offset + second.size and second.offset < (
                    first.offset + first.size
                ):
                    findings.append(
                        Finding(
                            Severity.WARNING,
                            f"{peripheral.name}: addressBlocks at offsets "
                            f"{first.offset:#x} and {second.offset:#x} overlap",
                        )
                    )
    return findings


def check_peripheral_overlap(device: Device) -> list[Finding]:
    """Flag two peripherals occupying overlapping address ranges (completes B2).

    Each peripheral's extent is its ``addressBlock`` interval(s)
    ``[base+offset, base+offset+size)``, or -- absent a block -- the span of its
    registers. Two different peripherals whose extents intersect claim the same
    bytes: a hardware contradiction unless declared as ``alternatePeripheral``
    (the nRF shared-engine case). regforge does not parse ``alternatePeripheral``
    yet, so for now **every** overlap is flagged (``ERROR``); suppression for
    declared alternates is the remaining B2 piece (see TODO).
    """
    findings: list[Finding] = []
    unit_bits = device.address_unit_bits
    extents: list[tuple[int, str, int, int]] = []  # (peripheral index, name, start, end)
    for index, peripheral in enumerate(device.peripherals):
        base = peripheral.base_address
        if peripheral.address_blocks:
            for block in peripheral.address_blocks:
                start = base + units_to_bytes(block.offset, unit_bits)
                extents.append(
                    (index, peripheral.name, start, start + units_to_bytes(block.size, unit_bits))
                )
        else:
            span = registers_end(peripheral, unit_bits)
            extents.append((index, peripheral.name, base, base + max(span, 1)))
    for i in range(len(extents)):
        for j in range(i + 1, len(extents)):
            index_a, name_a, start_a, end_a = extents[i]
            index_b, name_b, start_b, end_b = extents[j]
            if index_a == index_b:
                continue  # a peripheral's own blocks are check_address_blocks's job
            if start_a < end_b and start_b < end_a:
                findings.append(
                    Finding(
                        Severity.ERROR,
                        f"{name_a} and {name_b} occupy overlapping address ranges "
                        f"[{start_a:#x}, {end_a:#x}) / [{start_b:#x}, {end_b:#x}) -- "
                        "not declared as alternatePeripheral",
                    )
                )
    return findings


#: Every consistency check, run in order by :func:`run_checks`. Add a new check
#: here and it is picked up by the CLI and any other caller automatically.
ALL_CHECKS = (
    check_address_math,
    check_address_blocks,
    check_unowned_gaps,
    check_peripheral_overlap,
    check_derived_chains,
    check_derived_interrupts,
    check_group_divergence,
)


def run_checks(device: Device) -> list[Finding]:
    """Run every consistency check over ``device`` and return all findings."""
    findings: list[Finding] = []
    for check in ALL_CHECKS:
        findings.extend(check(device))
    return findings

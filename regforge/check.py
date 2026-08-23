"""Static consistency checks over the IR (the core of ``regforge check``).

These checks read only parsed IR fields, so they run the moment a device
loads -- no emitter, target, or external tool involved. Findings are advisory
(:attr:`Severity.WARNING`) unless they encode an internal contradiction that
no real hardware could satisfy (:attr:`Severity.ERROR`): a bus that cannot
address a whole unit is impossible; a register wider than the bus is merely
unusual (a multi-access register), so a human decides.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .families import first_divergence, layout_signature
from .ir import Device


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


def check_address_math(device: Device) -> list[Finding]:
    """Check that address units, bus width, and register sizes agree.

    The pair ``(address_unit_bits, bus_width)`` defines the device's address
    math; every register's size and offset must be consistent with it.

    Note:
        Register-array (``dim``) stride checks are omitted until arrays are
        represented in the IR. Cluster walking is likewise deferred.
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
        for register in peripheral.registers:
            name = f"{peripheral.name}.{register.name}"
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
            if units_per_register and register.address_offset % units_per_register != 0:
                findings.append(
                    Finding(
                        Severity.WARNING,
                        f"{name}: offset {register.address_offset:#x} is misaligned "
                        f"for a {register.size}-bit register",
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
                    f"groupName '{group}': members have differing register layouts "
                    f"(first differs at {register}) -- the label is not one verified "
                    "type; regforge emits separate types",
                )
            )
    return findings


#: Every consistency check, run in order by :func:`run_checks`. Add a new check
#: here and it is picked up by the CLI and any other caller automatically.
ALL_CHECKS = (
    check_address_math,
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

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

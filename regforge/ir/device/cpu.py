"""The processor core a device is built around."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Cpu:
    """The processor core a device is built around.

    Every field is optional: vendor descriptions routinely omit some, and
    several fields (``nvic_prio_bits``, ``vtor_present``, ``vendor_systick``)
    are specific to Arm Cortex-M cores. A reader for another architecture
    leaves the inapplicable fields ``None``; writers emit only what is present,
    never guessing at absent or suspect values.

    Attributes:
        name: Core identifier, e.g. ``"CM0PLUS"``.
        revision: Core revision, e.g. ``"r0p1"``.
        endian: Byte order, e.g. ``"little"`` or ``"big"``.
        mpu_present: Whether a memory protection unit is present.
        fpu_present: Whether a floating-point unit is present.
        vtor_present: Whether the vector table offset register is present.
        nvic_prio_bits: Implemented interrupt priority bits (Cortex-M).
        vendor_systick: Whether the vendor replaced the standard SysTick.
        num_interrupts: Number of device interrupt lines.
    """

    name: str | None = None
    revision: str | None = None
    endian: str | None = None
    mpu_present: bool | None = None
    fpu_present: bool | None = None
    vtor_present: bool | None = None
    nvic_prio_bits: int | None = None
    vendor_systick: bool | None = None
    num_interrupts: int | None = None

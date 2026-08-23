"""Device interrupt topology derived from peripheral <interrupt> elements.

CMSIS keeps the IRQ *numbers* (a real ``IRQn_Type`` enum) but flattens the
peripheral->interrupt containment the SVD carries into one global namespace.
This module rebuilds the device-wide view emitters need: the deduplicated IRQ
enumerators (here) and -- as later points land -- the per-instance links and
shared-vector detection.
"""

from __future__ import annotations

from .ir import Device, Interrupt


def all_interrupts(device: Device) -> list[Interrupt]:
    """Every distinct interrupt across the device, sorted by vector number.

    One interrupt may be referenced by several peripherals (a shared vector,
    e.g. STM32's ``TIM1_BRK_TIM9``); it appears once here. Deduplicated by name,
    sorted by ``(value, name)`` so the emitted enum is stable and gaps between
    vector numbers are simply left as gaps.
    """
    by_name: dict[str, Interrupt] = {}
    for peripheral in device.peripherals:
        for interrupt in peripheral.interrupts:
            by_name.setdefault(interrupt.name, interrupt)
    return sorted(by_name.values(), key=lambda i: (i.value, i.name))


def shared_vectors(device: Device) -> dict[int, list[str]]:
    """Vector value -> peripheral names sharing it, for values used by >1 peripheral.

    A shared vector is one interrupt *number* raised by several peripherals (nRF's
    serial blocks, STM32's ``TIM1_BRK_TIM9``): the vector table has a single slot,
    so one handler fires for all of them and must demultiplex. Keyed on ``value``
    (not name) so it catches peripherals that name the same vector differently.
    Names are kept in device declaration order; singleton vectors are omitted.

    This surfaces the fact (the emitter turns it into a point-of-use comment); it
    does not enforce anything -- the structural fix belongs to vector-table
    generation, which owns the handler binding.
    """
    by_value: dict[int, list[str]] = {}
    for peripheral in device.peripherals:
        for interrupt in peripheral.interrupts:
            names = by_value.setdefault(interrupt.value, [])
            if peripheral.name not in names:
                names.append(peripheral.name)
    return {value: names for value, names in by_value.items() if len(names) > 1}

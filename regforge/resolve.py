"""Defaults resolution: fill inherited register-property values into the IR.

``size``, ``access``, ``resetValue``, and ``resetMask`` may be declared at the
device, peripheral, register, or (for ``access``) field level, each inheriting
from the level above when silent. Vendors pick different levels -- nRF declares
``access`` at the register, RP2040 per field, STM32 leans on device defaults --
so a parser that handles only one style produces wrong access rights on the
others.

This pass runs once, after parsing (and after any future patch pass), before
``derivedFrom``/``dim`` expansion. It resolves every value into the IR so that
each downstream consumer -- every emitter, the docs generator, the linter --
reads identical resolved values and none can re-derive the chain differently.

Where ARM's SVDConv silently falls back to ``read-write`` when access is absent
at every level, this pass makes the same choice (it is the only sane default)
but *warns*, so the fallback is visible and auditable.
"""

from __future__ import annotations

from typing import TypeVar

from .ir import Access, Device

_T = TypeVar("_T")


def _first(*values: _T | None) -> _T | None:
    """Return the first value that is not ``None`` (``None`` if all are)."""
    for value in values:
        if value is not None:
            return value
    return None


def resolve_defaults(device: Device) -> list[str]:
    """Fill inherited size/access/reset values into every register and field.

    Mutates ``device`` in place and returns human-readable warnings -- one per
    register whose access is unspecified at every level and falls back to
    read-write.
    """
    warnings: list[str] = []

    device_size = _first(device.default_size, device.bus_width)
    device_access = device.default_access
    device_reset_value = device.default_reset_value
    device_reset_mask = device.default_reset_mask

    for peripheral in device.peripherals:
        peripheral_size = _first(peripheral.default_size, device_size)
        peripheral_access = _first(peripheral.default_access, device_access)
        peripheral_reset_value = _first(peripheral.default_reset_value, device_reset_value)
        peripheral_reset_mask = _first(peripheral.default_reset_mask, device_reset_mask)

        for register in peripheral.registers:
            register.size = _first(register.size, peripheral_size)
            register.reset_value = _first(register.reset_value, peripheral_reset_value)
            register.reset_mask = _first(register.reset_mask, peripheral_reset_mask)

            access = _first(register.access, peripheral_access)
            if access is None:
                access = Access.READ_WRITE
                warnings.append(
                    f"{peripheral.name}.{register.name}: access unspecified at every "
                    "level -- defaulting to read-write (unverified)"
                )
            register.access = access

            for field_ in register.fields:
                field_.access = _first(field_.access, register.access)

    return warnings

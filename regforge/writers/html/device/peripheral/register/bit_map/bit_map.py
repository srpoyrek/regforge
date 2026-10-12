"""The HTML block of a register's bit map."""

from __future__ import annotations

from dataclasses import dataclass

from markupsafe import Markup

from regforge.ir import Register
from regforge.writers.html.context import ElementHtml, RenderContext
from regforge.writers.html.device.device_facts import DeviceFacts
from regforge.writers.html.device.peripheral.register.bit_map.bit import BitHtml


@dataclass
class _Cell:
    label: str
    span: int
    claimed: bool


class BitMapHtml(ElementHtml):
    """Renders a register's bits: numbers, the field over each run of bits, reset values."""

    def __init__(self, context: RenderContext) -> None:
        super().__init__(context)
        self._bit = BitHtml()

    def render(self, register: Register, facts: DeviceFacts) -> Markup:
        """The bit map, most-significant bit first, wrapped at the bus width.

        Empty while the register's size is unresolved.
        """
        if register.size is None:
            return Markup("")
        bits = register.bits()
        rows = []
        for high in range(register.size, 0, -facts.bus_width):
            chunk = bits[max(0, high - facts.bus_width) : high][::-1]
            cells: list[_Cell] = []
            keys: list[tuple[int, int] | None] = []
            for bit in chunk:
                key = self._bit.key(bit)
                if cells and keys[-1] == key:
                    cells[-1].span += 1
                    continue
                cells.append(_Cell(self._bit.label(bit), 1, bit.field is not None))
                keys.append(key)
            rows.append(
                {
                    "numbers": [bit.position for bit in chunk],
                    "cells": cells,
                    "resets": [self._bit.reset(bit) for bit in chunk],
                }
            )
        return self._fill("bit_map.html.j2", rows=rows)

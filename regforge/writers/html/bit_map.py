"""The HTML block of a register's bit map."""

from __future__ import annotations

from dataclasses import dataclass

from markupsafe import Markup

from regforge.ir import Bit, Field, Register
from regforge.writers.html.context import ElementHtml
from regforge.writers.html.wording import NO_VALUE

#: Bits shown per row; a wider register wraps onto more rows.
ROW_BITS = 32


@dataclass
class _Cell:
    label: str
    span: int
    claimed: bool


def _copy_of(field_: Field, position: int) -> int:
    """Which copy of an array field covers ``position``; 0 for a plain field."""
    if field_.dim is None:
        return 0
    return (position - field_.bit_offset) // field_.dim.stride


def _key(bit: Bit) -> tuple[int, int] | None:
    if bit.field is None:
        return None
    return (id(bit.field), _copy_of(bit.field, bit.position))


def _label(bit: Bit) -> str:
    if bit.field is None:
        return ""
    if bit.field.dim is None:
        return bit.field.name
    return f"{bit.field.name}[{_copy_of(bit.field, bit.position)}]"


class BitMapHtml(ElementHtml):
    """Renders a register's bits: numbers, the field over each run of bits, reset values."""

    def render(self, register: Register) -> Markup:
        """The bit map, most-significant bit first; empty while the size is unresolved."""
        if register.size is None:
            return Markup("")
        bits = register.bits()
        rows = []
        for high in range(register.size, 0, -ROW_BITS):
            chunk = bits[max(0, high - ROW_BITS) : high][::-1]
            cells: list[_Cell] = []
            keys: list[tuple[int, int] | None] = []
            for bit in chunk:
                key = _key(bit)
                if cells and keys[-1] == key:
                    cells[-1].span += 1
                    continue
                cells.append(_Cell(_label(bit), 1, bit.field is not None))
                keys.append(key)
            rows.append(
                {
                    "numbers": [bit.position for bit in chunk],
                    "cells": cells,
                    "resets": [NO_VALUE if bit.reset is None else str(bit.reset) for bit in chunk],
                }
            )
        return self._fill("bit_map.html.j2", rows=rows)

"""The HTML block of one register."""

from __future__ import annotations

from markupsafe import Markup

from regforge.ir import Peripheral
from regforge.writers.html.bit_map import BitMapHtml
from regforge.writers.html.context import ElementHtml, RenderContext
from regforge.writers.html.field import FieldHtml
from regforge.writers.html.placement import PlacedRegister
from regforge.writers.html.wording import (
    NO_VALUE,
    access_label,
    anchor,
    array_note,
    effects,
    hex_,
    protection_text,
    register_reset,
    register_reset_mask,
    short,
)


class RegisterHtml(ElementHtml):
    """Renders one :class:`~regforge.ir.Register`: its facts, bit map and field table."""

    def __init__(self, context: RenderContext) -> None:
        super().__init__(context)
        self._bit_map = BitMapHtml(context)
        self._field = FieldHtml(context)

    def render(self, peripheral: Peripheral, placed: PlacedRegister) -> Markup:
        """The register's full block."""
        register = placed.register
        notes = effects(register)
        if register.protection is not None:
            notes.append(protection_text(register.protection))
        if register.data_type is not None:
            notes.append(f"accessed as {register.data_type.value}")
        own = array_note(register, "units")
        array = " -- ".join(n for n in (placed.note, own) if n) or None
        return self._fill(
            "register.html.j2",
            anchor=anchor(peripheral.name, placed.path),
            path=placed.path,
            display_name=register.display_name,
            offset=hex_(placed.offset, 4),
            address=hex_(peripheral.base_address + placed.offset, 8),
            size=NO_VALUE if register.size is None else f"{register.size} bits",
            access=access_label(register.access),
            reset=register_reset(register),
            reset_mask=register_reset_mask(register),
            description=register.description,
            array_note=array,
            alternates=[n for n in register.alternates if n != register.name],
            notes=notes,
            bit_map=self._bit_map.render(register),
            fields=[self._field.render(register, f) for f in register.fields],
        )

    def row(self, peripheral: Peripheral, placed: PlacedRegister) -> Markup:
        """The register's line in its peripheral's summary table."""
        register = placed.register
        return self._fill(
            "register_row.html.j2",
            anchor=anchor(peripheral.name, placed.path),
            path=placed.path,
            offset=hex_(placed.offset, 4),
            size=NO_VALUE if register.size is None else f"{register.size} bits",
            access=access_label(register.access),
            reset=register_reset(register),
            summary=short(register.description),
        )

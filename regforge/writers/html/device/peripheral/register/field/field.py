"""The HTML block of one field."""

from __future__ import annotations

from markupsafe import Markup

from regforge.ir import Field, Register
from regforge.writers.html.context import ElementHtml, RenderContext
from regforge.writers.html.device.peripheral.dim import DimHtml
from regforge.writers.html.device.peripheral.register.access import AccessHtml
from regforge.writers.html.device.peripheral.register.field.enum_set.enum_set import EnumSetHtml
from regforge.writers.html.device.peripheral.register.reset import ResetHtml
from regforge.writers.html.device.peripheral.register.side_effects import SideEffectsHtml


class FieldHtml(ElementHtml):
    """Renders one :class:`~regforge.ir.Field` as a row of its register's field table.

    A field says its access, its reset and what a write or a read does in the same words as its
    register, so it uses the leaves of the register's folder.
    """

    def __init__(self, context: RenderContext) -> None:
        super().__init__(context)
        self._access = AccessHtml()
        self._dim = DimHtml()
        self._enum_set = EnumSetHtml(context)
        self._reset = ResetHtml()
        self._side_effects = SideEffectsHtml()

    def bits_label(self, field_: Field) -> str:
        """The field's bits as ``[7:4]``, or ``[3]`` for a single bit."""
        return field_.bit_range if field_.bit_width > 1 else f"[{field_.lsb}]"

    def render(self, register: Register, field_: Field) -> Markup:
        """The field's bits, name, access, reset value, description, values and notes."""
        notes = self._side_effects.notes(field_)
        array = self._dim.note(field_, "bits")
        if array is not None:
            notes.insert(0, array)
        several = len(field_.enum_sets) > 1
        sets = [
            self._enum_set.render(s, s.usage.value if several else None, field_.bit_width)
            for s in field_.enum_sets
            if s.values
        ]
        return self._fill(
            "field.html.j2",
            bits=self.bits_label(field_),
            name=field_.name,
            access=self._access.label(field_.access),
            reset=self._reset.field_value(register, field_),
            description=field_.description,
            enum_sets=sets,
            notes=notes,
        )

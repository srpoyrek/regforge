"""The HTML block of one field."""

from __future__ import annotations

from markupsafe import Markup

from regforge.ir import Field, Register
from regforge.writers.html.context import ElementHtml, RenderContext
from regforge.writers.html.enum_set import EnumSetHtml
from regforge.writers.html.wording import (
    access_label,
    array_note,
    bits_label,
    effects,
    field_reset,
)


class FieldHtml(ElementHtml):
    """Renders one :class:`~regforge.ir.Field` as a row of its register's field table."""

    def __init__(self, context: RenderContext) -> None:
        super().__init__(context)
        self._enum_set = EnumSetHtml(context)

    def render(self, register: Register, field_: Field) -> Markup:
        """The field's bits, name, access, reset value, description, values and notes."""
        notes = effects(field_)
        array = array_note(field_, "bits")
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
            bits=bits_label(field_),
            name=field_.name,
            access=access_label(field_.access),
            reset=field_reset(register, field_),
            description=field_.description,
            enum_sets=sets,
            notes=notes,
        )

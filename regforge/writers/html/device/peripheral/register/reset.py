"""The HTML wording of a reset value: a register's, its mask, and the share of it a field holds."""

from __future__ import annotations

from regforge.ir import Field, Register
from regforge.writers.html.context import LeafHtml
from regforge.writers.html.wording import NO_VALUE, hex_, hex_digits


class ResetHtml(LeafHtml):
    """Renders the reset value of a register and of its fields."""

    def register_value(self, register: Register) -> str:
        """The register's reset value as hex, or an en dash when it has none."""
        if register.reset_value is None or register.size is None:
            return NO_VALUE
        return hex_(register.reset_value, hex_digits(register.size))

    def register_mask(self, register: Register) -> str | None:
        """The register's reset mask as hex, or ``None`` when it has none."""
        if register.reset_mask is None or register.size is None:
            return None
        return hex_(register.reset_mask, hex_digits(register.size))

    def field_value(self, register: Register, field_: Field) -> str:
        """The value the field holds after reset, or an en dash when the register does not say."""
        if register.reset_value is None:
            return NO_VALUE
        if register.reset_mask is not None and register.reset_mask & field_.mask != field_.mask:
            return NO_VALUE
        return f"{field_.extract(register.reset_value):#x}"

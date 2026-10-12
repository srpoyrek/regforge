"""The HTML block of one register."""

from __future__ import annotations

from markupsafe import Markup

from regforge.ir import Peripheral
from regforge.writers.html.context import ElementHtml, RenderContext
from regforge.writers.html.device.device_facts import DeviceFacts
from regforge.writers.html.device.peripheral.dim import DimHtml
from regforge.writers.html.device.peripheral.placement import PlacedRegister
from regforge.writers.html.device.peripheral.register.access import AccessHtml
from regforge.writers.html.device.peripheral.register.bit_map.bit_map import BitMapHtml
from regforge.writers.html.device.peripheral.register.data_type import DataTypeHtml
from regforge.writers.html.device.peripheral.register.field.field import FieldHtml
from regforge.writers.html.device.peripheral.register.protection import ProtectionHtml
from regforge.writers.html.device.peripheral.register.reset import ResetHtml
from regforge.writers.html.device.peripheral.register.side_effects import SideEffectsHtml
from regforge.writers.html.wording import NO_VALUE, anchor, hex_, short


class RegisterHtml(ElementHtml):
    """Renders one :class:`~regforge.ir.Register`: its facts, bit map and field table.

    The register's own settings are worded by the leaves beside this module (access, data type,
    protection, reset, what a write or a read does); its bit map and its fields are blocks of
    their own, in the folders below.
    """

    def __init__(self, context: RenderContext) -> None:
        super().__init__(context)
        self._access = AccessHtml()
        self._bit_map = BitMapHtml(context)
        self._data_type = DataTypeHtml()
        self._dim = DimHtml()
        self._field = FieldHtml(context)
        self._protection = ProtectionHtml()
        self._reset = ResetHtml()
        self._side_effects = SideEffectsHtml()

    def render(self, peripheral: Peripheral, placed: PlacedRegister, facts: DeviceFacts) -> Markup:
        """The register's full block."""
        register = placed.register
        notes = self._side_effects.notes(register)
        if register.protection is not None:
            notes.append(self._protection.text(register.protection))
        own = self._dim.note(register, "units")
        array = " -- ".join(n for n in (placed.note, own) if n) or None
        return self._fill(
            "register.html.j2",
            anchor=anchor(peripheral.name, placed.path),
            path=placed.path,
            display_name=register.display_name,
            offset=hex_(placed.offset, facts.offset_digits),
            address=hex_(peripheral.base_address + placed.offset, facts.address_digits),
            size=NO_VALUE if register.size is None else f"{register.size} bits",
            access=self._access.label(register.access),
            data_type=self._data_type.label(register.data_type),
            reset=self._reset.register_value(register),
            reset_mask=self._reset.register_mask(register),
            description=register.description,
            array_note=array,
            alternates=list(placed.alternates),
            notes=notes,
            bit_map=self._bit_map.render(register, facts),
            fields=[self._field.render(register, f) for f in register.fields],
        )

    def row(self, peripheral: Peripheral, placed: PlacedRegister, facts: DeviceFacts) -> Markup:
        """The register's line in its peripheral's summary table."""
        register = placed.register
        return self._fill(
            "register_row.html.j2",
            anchor=anchor(peripheral.name, placed.path),
            path=placed.path,
            offset=hex_(placed.offset, facts.offset_digits),
            size=NO_VALUE if register.size is None else f"{register.size} bits",
            access=self._access.label(register.access),
            reset=self._reset.register_value(register),
            summary=short(register.description),
        )

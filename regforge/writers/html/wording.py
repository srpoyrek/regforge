"""The wording and number formats shared by the HTML renderers."""

from __future__ import annotations

from regforge.ir import (
    Access,
    Cluster,
    Field,
    ModifiedWriteValues,
    Peripheral,
    Protection,
    ReadAction,
    Register,
)

NO_VALUE = "–"

_ACCESS_LABEL = {
    Access.READ_ONLY: "RO",
    Access.WRITE_ONLY: "WO",
    Access.READ_WRITE: "RW",
    Access.WRITE_ONCE: "WO (once)",
    Access.READ_WRITE_ONCE: "RW (write once)",
}

_WRITE_TEXT = {
    ModifiedWriteValues.ONE_TO_CLEAR: "writing 1 clears the bit",
    ModifiedWriteValues.ONE_TO_SET: "writing 1 sets the bit",
    ModifiedWriteValues.ONE_TO_TOGGLE: "writing 1 toggles the bit",
    ModifiedWriteValues.ZERO_TO_CLEAR: "writing 0 clears the bit",
    ModifiedWriteValues.ZERO_TO_SET: "writing 0 sets the bit",
    ModifiedWriteValues.ZERO_TO_TOGGLE: "writing 0 toggles the bit",
    ModifiedWriteValues.CLEAR: "any write clears it",
    ModifiedWriteValues.SET: "any write sets it",
    ModifiedWriteValues.MODIFY: "a write modifies it in a way the hardware decides",
}

_READ_TEXT = {
    ReadAction.CLEAR: "a read clears it",
    ReadAction.SET: "a read sets it",
    ReadAction.MODIFY: "a read modifies it",
    ReadAction.MODIFY_EXTERNAL: "a read changes it from outside, as a FIFO pop does",
}

_PROTECTION_TEXT = {
    Protection.SECURE: "secure access only",
    Protection.NON_SECURE: "non-secure or secure access",
    Protection.PRIVILEGED: "privileged access only",
}


def hex_(value: int, digits: int) -> str:
    """``value`` as zero-padded upper-case hex, ``0x00FF``."""
    return f"0x{value:0{digits}X}"


def yes_no(value: bool) -> str:
    """``yes`` or ``no``."""
    return "yes" if value else "no"


def anchor(*parts: str) -> str:
    """An HTML id built from ``parts``."""
    return ".".join(parts).replace(" ", "_")


def short(text: str | None, limit: int = 90) -> str:
    """The first line of ``text``, cut to ``limit`` characters, for a summary table."""
    if not text or not text.strip():
        return ""
    first = text.strip().splitlines()[0].strip()
    return first if len(first) <= limit else first[: limit - 1].rstrip() + "…"


def access_label(access: Access | None) -> str:
    """``RO``, ``WO``, ``RW`` and so on; an en dash when unresolved."""
    return NO_VALUE if access is None else _ACCESS_LABEL[access]


def protection_text(protection: Protection) -> str:
    """What the protection setting requires of an access."""
    return _PROTECTION_TEXT[protection]


def array_note(element: Peripheral | Cluster | Register | Field, unit: str) -> str | None:
    """How an element relates to a ``<dim>`` array, or ``None`` for a plain element."""
    dim = element.dim
    if dim is not None and dim.array:
        return f"array of {dim.length}, {dim.stride:#x} {unit} apart"
    origin = element.origin
    if origin is not None:
        return f"copy {origin.index + 1} of {origin.count} of {origin.template}"
    return None


def effects(element: Register | Field) -> list[str]:
    """What reading and writing the element does, beyond storing and returning bits."""
    notes: list[str] = []
    write = element.modified_write_values
    if write is not None:
        text = _WRITE_TEXT[write]
        if write.acts_per_bit:
            text += "; write the bits you mean directly, as a read-modify-write would change others"
        notes.append(text)
    if element.read_action is not None:
        notes.append(_READ_TEXT[element.read_action] + "; do not read it just to look")
    if element.is_write_once:
        notes.append("can be written only once after reset")
    constraint = element.write_constraint
    if constraint is not None:
        if constraint.has_range:
            notes.append(f"valid values {constraint.minimum} to {constraint.maximum}")
        if constraint.use_enumerated_values:
            notes.append("only the listed values may be written")
        if constraint.write_as_read:
            notes.append("must be written back as it was read")
    return notes


def register_reset(register: Register) -> str:
    """The register's reset value as hex, or an en dash when it has none."""
    if register.reset_value is None or register.size is None:
        return NO_VALUE
    return hex_(register.reset_value, (register.size + 3) // 4)


def register_reset_mask(register: Register) -> str | None:
    """The register's reset mask as hex, or ``None`` when it has none."""
    if register.reset_mask is None or register.size is None:
        return None
    return hex_(register.reset_mask, (register.size + 3) // 4)


def field_reset(register: Register, field_: Field) -> str:
    """The value the field holds after reset, or an en dash when the register does not say."""
    if register.reset_value is None:
        return NO_VALUE
    if register.reset_mask is not None and register.reset_mask & field_.mask != field_.mask:
        return NO_VALUE
    return f"{field_.extract(register.reset_value):#x}"


def bits_label(field_: Field) -> str:
    """The field's bits as ``[7:4]``, or ``[3]`` for a single bit."""
    return field_.bit_range if field_.bit_width > 1 else f"[{field_.lsb}]"

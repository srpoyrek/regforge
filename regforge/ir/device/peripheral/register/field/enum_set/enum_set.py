"""An enumerated set: the named values of one field, as one SVD ``<enumeratedValues>``."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from regforge.ir.device.peripheral.register.field.enum_set.enum_usage import EnumUsage

if TYPE_CHECKING:
    from regforge.ir import EnumeratedValue

#: The widest field whose every number is listed one by one; a wider one is not enumerated.
MAX_LISTED_BITS = 16


@dataclass
class EnumSet:
    """The named values of a :class:`~regforge.ir.Field`, with the set's own settings.

    Each :class:`~regforge.ir.EnumeratedValue` names one number the field's bits can
    hold, a run of them, or (the catch-all entry) all the rest; the set is the whole list
    plus what the SVD says about it as a group.

    Attributes:
        values: The entries, in the order the source wrote them.
        name: The set's own name (SVD ``<name>``), which another set refers to
            from ``derived_from``; ``None`` when absent.
        header_enum_name: SVD ``headerEnumName`` -- the vendor's preferred name for
            the enum type; ``None`` when absent.
        usage: Whether the set describes reads, writes or both; ``READ_WRITE``
            when the source omits it, as the SVD schema defaults.
        derived_from: Name (or dotted path) of the set whose values this one reuses
            (SVD ``derivedFrom``). A reference, not Python inheritance: it is kept
            as written, and a later resolve pass copies the values across, as it
            does for a peripheral.
    """

    values: list[EnumeratedValue] = field(default_factory=list)
    name: str | None = None
    header_enum_name: str | None = None
    usage: EnumUsage = EnumUsage.READ_WRITE
    derived_from: str | None = None

    @property
    def default_entry(self) -> EnumeratedValue | None:
        """The catch-all entry (SVD ``isDefault``), or ``None``."""
        return next((v for v in self.values if v.is_default), None)

    def entry_for(self, number: int, include_default: bool = True) -> EnumeratedValue | None:
        """The entry that names ``number``: the first explicit match, else the catch-all.

        ``include_default=False`` leaves the catch-all out, so only a number the file
        names on purpose is found.
        """
        match = next((v for v in self.values if v.matches(number)), None)
        if match is None and include_default:
            return self.default_entry
        return match

    def name_of(self, number: int) -> str | None:
        """The name of the entry that names ``number``, or ``None`` if none does."""
        entry = self.entry_for(number)
        return entry.name if entry is not None else None

    def value_of(self, name: str) -> int | None:
        """The number of the entry called ``name``; ``None`` if none, or if it is a catch-all."""
        return next((v.value for v in self.values if v.name == name), None)

    def oversized(self, bit_width: int) -> list[EnumeratedValue]:
        """The entries whose number does not fit in ``bit_width`` bits."""
        return [v for v in self.values if not v.fits_in(bit_width)]

    @property
    def numbers(self) -> list[int]:
        """The number of every entry that has one, in order."""
        return [v.value for v in self.values if v.value is not None]

    def duplicate_numbers(self) -> list[int]:
        """The numbers more than one entry names, in the order they first repeat."""
        seen: set[int] = set()
        repeated: list[int] = []
        for number in self.numbers:
            if number in seen and number not in repeated:
                repeated.append(number)
            seen.add(number)
        return repeated

    def duplicate_names(self) -> list[str]:
        """The names more than one entry uses, in the order they first repeat."""
        seen: set[str] = set()
        repeated: list[str] = []
        for v in self.values:
            if v.name in seen and v.name not in repeated:
                repeated.append(v.name)
            seen.add(v.name)
        return repeated

    def is_complete(self, bit_width: int) -> bool:
        """Whether every number a ``bit_width``-bit field can hold is named.

        A catch-all entry names the rest, so it makes the set complete. A field wider than
        ``MAX_LISTED_BITS`` is too wide to check number by number, so only a catch-all
        completes it.
        """
        if self.default_entry is not None:
            return True
        return bit_width <= MAX_LISTED_BITS and not self.gaps(bit_width)

    def gaps(self, bit_width: int) -> list[int]:
        """The numbers a ``bit_width``-bit field can hold that no entry names.

        Empty when a catch-all entry covers them. ``ValueError`` for a field wider
        than ``MAX_LISTED_BITS``, which is too wide to list.
        """
        if bit_width > MAX_LISTED_BITS:
            raise ValueError(f"{bit_width} bits is too wide to list the gaps")
        return [n for n in range(1 << bit_width) if self.entry_for(n) is None]

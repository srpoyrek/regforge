"""An enumerated set: the named values of one field, as one SVD ``<enumeratedValues>``."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from regforge.ir.enum_usage import EnumUsage

if TYPE_CHECKING:
    from regforge.ir import EnumeratedValue


@dataclass
class EnumSet:
    """The named values of a :class:`~regforge.ir.Field`, with the set's own settings.

    Each :class:`~regforge.ir.EnumeratedValue` names one number the field's bits can
    hold; the set is the whole list plus what the SVD says about it as a group.

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

    def name_of(self, number: int) -> str | None:
        """The name of the first entry holding ``number``, or ``None`` if none does."""
        return next((v.name for v in self.values if v.value == number), None)

    def value_of(self, name: str) -> int | None:
        """The number of the entry called ``name``, or ``None`` if there is none."""
        return next((v.value for v in self.values if v.name == name), None)

    def oversized(self, bit_width: int) -> list[EnumeratedValue]:
        """The entries whose number does not fit in ``bit_width`` bits."""
        return [v for v in self.values if not v.fits_in(bit_width)]

    @property
    def numbers(self) -> list[int]:
        """The number of every entry, in order."""
        return [v.value for v in self.values]

    @property
    def default_entry(self) -> EnumeratedValue | None:
        """The catch-all entry (SVD ``isDefault``), or ``None``."""
        return next((v for v in self.values if v.is_default), None)

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

        A catch-all entry names the rest, so it makes the set complete.
        """
        if self.default_entry is not None:
            return True
        named = {n for n in self.numbers if 0 <= n < (1 << bit_width)}
        return len(named) == 1 << bit_width

    def gaps(self, bit_width: int) -> list[int]:
        """The numbers a ``bit_width``-bit field can hold that no entry names.

        Empty when a catch-all entry covers them. ``ValueError`` for a field wider
        than 16 bits, which is too wide to list.
        """
        if bit_width > 16:
            raise ValueError(f"{bit_width} bits is too wide to list the gaps")
        if self.default_entry is not None:
            return []
        named = set(self.numbers)
        return [n for n in range(1 << bit_width) if n not in named]

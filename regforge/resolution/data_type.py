"""The rules of a data type: the integer a register is meant to be read as, and its size."""

from __future__ import annotations

from regforge.finding import Finding, Severity
from regforge.ir import DataType
from regforge.resolution.base import Resolution


class DataTypeResolution(Resolution):
    """The data type of a register, as the rules see it, beside the register's size.

    A data type names an integer of a fixed width: ``uint16_t`` is 16 bits. It contradicts a
    register of another size (``WARNING``): the file disagrees with itself, though the
    hardware could still be as it says. A pointer type holds an address, whose width depends
    on the processor, so it is not compared; neither is a register whose size is still
    unresolved. The class knows only the type and the size, not what carries them.

    Attributes:
        data_type: The data type.
        size: The size in bits of the register that carries it; ``None`` while unresolved.
        where: The dotted path of that register, which starts every message.
    """

    def __init__(self, data_type: DataType, size: int | None, where: str) -> None:
        self.data_type = data_type
        self.size = size
        self.where = where

    def findings(self) -> list[Finding]:
        """A data type whose width is not the register's."""
        if self.data_type.is_pointer or self.size is None or self.data_type.bits == self.size:
            return []
        return [
            Finding(
                Severity.WARNING,
                f"{self.where}: dataType {self.data_type.value} is {self.data_type.bits} bits "
                f"wide, but the register is {self.size} bits",
            )
        ]

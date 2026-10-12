"""The C data type an SVD register is meant to be accessed as."""

from __future__ import annotations

from enum import Enum


class DataType(Enum):
    """A register's data type (SVD ``<dataType>``), spelled as in SVD.

    The SVD fixes the list: fixed-width integers and pointers to them.
    """

    UINT8 = "uint8_t"
    UINT16 = "uint16_t"
    UINT32 = "uint32_t"
    UINT64 = "uint64_t"
    INT8 = "int8_t"
    INT16 = "int16_t"
    INT32 = "int32_t"
    INT64 = "int64_t"
    UINT8_PTR = "uint8_t *"
    UINT16_PTR = "uint16_t *"
    UINT32_PTR = "uint32_t *"
    UINT64_PTR = "uint64_t *"
    INT8_PTR = "int8_t *"
    INT16_PTR = "int16_t *"
    INT32_PTR = "int32_t *"
    INT64_PTR = "int64_t *"

    @property
    def is_pointer(self) -> bool:
        """Whether the type is a pointer to an integer."""
        return self.value.endswith("*")

    @property
    def is_signed(self) -> bool:
        """Whether the integer is signed."""
        return self.value.startswith("int")

    @property
    def bits(self) -> int:
        """Width in bits of the integer (the pointed-to integer for a pointer)."""
        return _BITS[self]

    @property
    def base(self) -> DataType:
        """The integer type itself: the pointed-to type for a pointer."""
        return DataType(self.value.removesuffix(" *"))

    @property
    def pointer(self) -> DataType:
        """The pointer to this integer type."""
        return DataType(f"{self.base.value} *")


#: Width in bits of each type's integer (the pointed-to integer for a pointer).
_BITS = {
    DataType.UINT8: 8,
    DataType.UINT16: 16,
    DataType.UINT32: 32,
    DataType.UINT64: 64,
    DataType.INT8: 8,
    DataType.INT16: 16,
    DataType.INT32: 32,
    DataType.INT64: 64,
    DataType.UINT8_PTR: 8,
    DataType.UINT16_PTR: 16,
    DataType.UINT32_PTR: 32,
    DataType.UINT64_PTR: 64,
    DataType.INT8_PTR: 8,
    DataType.INT16_PTR: 16,
    DataType.INT32_PTR: 32,
    DataType.INT64_PTR: 64,
}

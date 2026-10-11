"""DataType: the C type an SVD register is meant to be accessed as."""

from regforge.ir import DataType


def test_values_are_spelled_as_in_svd():
    assert DataType.UINT8.value == "uint8_t"
    assert DataType.INT64.value == "int64_t"
    assert DataType.UINT32_PTR.value == "uint32_t *"
    assert len(DataType) == 16


def test_pointer_types_are_pointers_and_integers_are_not():
    assert DataType.UINT32_PTR.is_pointer
    assert not DataType.UINT32.is_pointer
    assert sum(1 for t in DataType if t.is_pointer) == 8


def test_signedness_follows_the_int_and_uint_prefix():
    assert DataType.INT16.is_signed and DataType.INT16_PTR.is_signed
    assert not DataType.UINT16.is_signed and not DataType.UINT16_PTR.is_signed


def test_bits_is_the_width_of_the_integer():
    assert [DataType.UINT8.bits, DataType.INT16.bits, DataType.UINT32.bits] == [8, 16, 32]
    assert DataType.INT64_PTR.bits == 64  # the pointed-to integer


def test_base_is_the_integer_type_and_pointer_is_its_pointer():
    assert DataType.UINT32_PTR.base is DataType.UINT32
    assert DataType.UINT32.base is DataType.UINT32
    assert DataType.INT8.pointer is DataType.INT8_PTR
    assert DataType.INT8_PTR.pointer is DataType.INT8_PTR


def test_every_type_has_a_width():
    # A new member without an entry in the width table would raise KeyError here.
    assert {t.bits for t in DataType} == {8, 16, 32, 64}

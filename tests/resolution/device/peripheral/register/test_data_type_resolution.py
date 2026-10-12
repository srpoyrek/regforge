"""DataTypeResolution: the integer a register is meant to be read as, beside its size."""

import inspect

import pytest

import regforge.resolution.device.peripheral.register.data_type as type_module
from regforge.finding import Severity
from regforge.ir import DataType
from regforge.resolution import DataTypeResolution

INTEGERS = [data_type for data_type in DataType if not data_type.is_pointer]
POINTERS = [data_type for data_type in DataType if data_type.is_pointer]


def _res(data_type: DataType, size: int | None) -> DataTypeResolution:
    return DataTypeResolution(data_type, size, "P.R")


def test_a_type_of_another_width_than_the_register_is_a_warning():
    (finding,) = _res(DataType.UINT16, 32).findings()
    assert finding.severity is Severity.WARNING
    assert finding.message == "P.R: dataType uint16_t is 16 bits wide, but the register is 32 bits"


@pytest.mark.parametrize("data_type", INTEGERS)
def test_a_type_as_wide_as_the_register_is_silent(data_type):
    assert _res(data_type, data_type.bits).findings() == []


@pytest.mark.parametrize("data_type", INTEGERS)
def test_every_integer_type_is_reported_on_a_register_of_another_size(data_type):
    other = 16 if data_type.bits != 16 else 32
    assert len(_res(data_type, other).findings()) == 1


def test_a_signed_type_is_compared_by_its_width_like_an_unsigned_one():
    assert _res(DataType.INT8, 8).findings() == []
    assert _res(DataType.INT64, 32).findings() != []


@pytest.mark.parametrize("data_type", POINTERS)
def test_a_pointer_type_is_not_compared(data_type):
    for size in (8, 16, 32, 64):
        assert _res(data_type, size).findings() == []


def test_a_register_with_no_resolved_size_is_not_compared():
    assert _res(DataType.UINT8, None).findings() == []


def test_str_is_the_report():
    assert str(_res(DataType.INT64, 32)) == (
        "warning: P.R: dataType int64_t is 64 bits wide, but the register is 32 bits"
    )
    assert str(_res(DataType.INT32, 32)) == ""


# --- layering ----------------------------------------------------------------------


def test_the_class_knows_nothing_above_a_data_type():
    source = inspect.getsource(type_module)
    for above in ("Field", "Register", "Peripheral", "Cluster", "Device"):
        assert above not in source

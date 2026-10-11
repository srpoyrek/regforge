"""ModifiedWriteValuesResolution: what a write does, against the access it is written beside."""

import inspect

import pytest

import regforge.resolution.modified_write_values as write_module
from regforge.finding import Severity
from regforge.ir import Access, ModifiedWriteValues
from regforge.resolution import ModifiedWriteValuesResolution


def _res(value: ModifiedWriteValues, access: Access | None) -> ModifiedWriteValuesResolution:
    return ModifiedWriteValuesResolution(value, access, "P.R.F")


def test_a_write_behaviour_beside_a_read_only_access_is_a_warning():
    (finding,) = _res(ModifiedWriteValues.ONE_TO_CLEAR, Access.READ_ONLY).findings()
    assert finding.severity is Severity.WARNING
    assert finding.message == (
        "P.R.F: modifiedWriteValues oneToClear describes a write, but access is read-only"
    )


@pytest.mark.parametrize("value", list(ModifiedWriteValues))
def test_every_behaviour_is_reported_on_a_read_only_access(value):
    (finding,) = _res(value, Access.READ_ONLY).findings()
    assert f"modifiedWriteValues {value.value} describes a write" in finding.message


def test_modify_is_reported_too_though_it_is_the_default():
    findings = _res(ModifiedWriteValues.MODIFY, Access.READ_ONLY).findings()
    assert [finding.message for finding in findings] == [
        "P.R.F: modifiedWriteValues modify describes a write, but access is read-only"
    ]


@pytest.mark.parametrize(
    "access", [Access.READ_WRITE, Access.WRITE_ONLY, Access.WRITE_ONCE, Access.READ_WRITE_ONCE]
)
def test_an_access_that_can_write_is_silent(access):
    assert _res(ModifiedWriteValues.ONE_TO_CLEAR, access).findings() == []


def test_an_unresolved_access_counts_as_read_write():
    assert _res(ModifiedWriteValues.ZERO_TO_SET, None).findings() == []


def test_str_is_the_report():
    report = str(_res(ModifiedWriteValues.CLEAR, Access.READ_ONLY))
    assert report == (
        "warning: P.R.F: modifiedWriteValues clear describes a write, but access is read-only"
    )
    assert str(_res(ModifiedWriteValues.CLEAR, Access.READ_WRITE)) == ""


# --- layering ----------------------------------------------------------------------


def test_the_class_knows_nothing_above_a_write_behaviour():
    source = inspect.getsource(write_module)
    for above in ("Field", "Register", "Peripheral", "Cluster", "Device"):
        assert above not in source

"""ReadActionResolution: what a read does, against the access it is written beside."""

import inspect

import pytest

import regforge.resolution.device.peripheral.register.read_action as read_module
from regforge.finding import Severity
from regforge.ir import Access, ReadAction
from regforge.resolution import ReadActionResolution


def _res(value: ReadAction, access: Access | None) -> ReadActionResolution:
    return ReadActionResolution(value, access, "P.R")


def test_a_read_action_beside_a_write_only_access_is_a_warning():
    (finding,) = _res(ReadAction.CLEAR, Access.WRITE_ONLY).findings()
    assert finding.severity is Severity.WARNING
    assert finding.message == "P.R: readAction clear describes a read, but access is write-only"


@pytest.mark.parametrize("value", list(ReadAction))
def test_every_action_is_reported_on_a_write_only_access(value):
    (finding,) = _res(value, Access.WRITE_ONLY).findings()
    assert f"readAction {value.value} describes a read" in finding.message


def test_a_write_once_access_cannot_be_read_back_either():
    findings = _res(ReadAction.MODIFY_EXTERNAL, Access.WRITE_ONCE).findings()
    assert [finding.message for finding in findings] == [
        "P.R: readAction modifyExternal describes a read, but access is writeOnce"
    ]


@pytest.mark.parametrize("access", [Access.READ_ONLY, Access.READ_WRITE, Access.READ_WRITE_ONCE])
def test_an_access_that_can_read_is_silent(access):
    assert _res(ReadAction.CLEAR, access).findings() == []


def test_an_unresolved_access_counts_as_read_write():
    assert _res(ReadAction.MODIFY, None).findings() == []


def test_str_is_the_report():
    report = str(_res(ReadAction.SET, Access.WRITE_ONLY))
    assert report == "warning: P.R: readAction set describes a read, but access is write-only"
    assert str(_res(ReadAction.SET, Access.READ_ONLY)) == ""


# --- layering ----------------------------------------------------------------------


def test_the_class_knows_nothing_above_a_read_action():
    source = inspect.getsource(read_module)
    for above in ("Field", "Register", "Peripheral", "Cluster", "Device"):
        assert above not in source

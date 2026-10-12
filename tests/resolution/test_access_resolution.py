"""AccessResolution: the access of a field, beside the access of its register."""

import inspect

import pytest

import regforge.resolution.access as access_module
from regforge.finding import Severity
from regforge.ir import Access
from regforge.resolution import AccessResolution

RO, WO, RW = Access.READ_ONLY, Access.WRITE_ONLY, Access.READ_WRITE
WRITE_ONCE, RW_ONCE = Access.WRITE_ONCE, Access.READ_WRITE_ONCE


def _res(access: Access | None, within: Access | None) -> AccessResolution:
    return AccessResolution(access, within, "P.R.F")


def test_a_field_that_can_be_written_in_a_read_only_register_is_a_warning():
    (finding,) = _res(RW, RO).findings()
    assert finding.severity is Severity.WARNING
    assert finding.message == "P.R.F: access is read-write, but its register is read-only"


@pytest.mark.parametrize(
    ("access", "within"),
    [
        (RW, RO),
        (WO, RO),
        (WRITE_ONCE, RO),
        (RW_ONCE, RO),
        (RW, WO),
        (RO, WO),
        (RO, WRITE_ONCE),
        (RW, WRITE_ONCE),
    ],
)
def test_an_access_beyond_the_registers_is_reported(access, within):
    assert len(_res(access, within).findings()) == 1


@pytest.mark.parametrize(
    ("access", "within"),
    [
        (RO, RO),
        (RO, RW),
        (WO, WO),
        (WO, RW),
        (RW, RW),
        (RO, RW_ONCE),
        (WRITE_ONCE, WO),
        (RW, RW_ONCE),
    ],
)
def test_an_access_the_register_allows_is_silent(access, within):
    assert _res(access, within).findings() == []


def test_the_message_names_both_accesses_as_the_schema_spells_them():
    findings = _res(RW, WRITE_ONCE).findings()
    assert [finding.message for finding in findings] == [
        "P.R.F: access is read-write, but its register is writeOnce"
    ]


def test_an_access_that_is_unresolved_contradicts_nothing():
    assert _res(None, RO).findings() == []
    assert _res(RW, None).findings() == []
    assert _res(None, None).findings() == []


def test_str_is_the_report():
    assert (
        str(_res(WO, RO)) == "warning: P.R.F: access is write-only, but its register is read-only"
    )
    assert str(_res(RO, RO)) == ""


# --- layering ----------------------------------------------------------------------


def test_the_class_knows_nothing_above_an_access():
    source = inspect.getsource(access_module)
    for above in ("Field", "Register", "Peripheral", "Cluster", "Device"):
        assert above not in source

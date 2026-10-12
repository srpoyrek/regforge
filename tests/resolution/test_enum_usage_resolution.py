"""EnumUsageResolution: the direction an enumerated set describes, and how it compares."""

import inspect

import regforge.resolution.enum_usage as usage_module
from regforge.finding import Severity
from regforge.ir import Access, EnumUsage
from regforge.resolution import EnumUsageResolution


def _res(usage: EnumUsage, owner: str) -> EnumUsageResolution:
    return EnumUsageResolution(usage, owner, "P.R.F")


def _messages(findings):
    return [finding.message for finding in findings]


def test_each_usage_occupies_its_directions():
    assert _res(EnumUsage.READ, "A").ranges() == [(0, 0)]
    assert _res(EnumUsage.WRITE, "A").ranges() == [(1, 1)]
    assert _res(EnumUsage.READ_WRITE, "A").ranges() == [(0, 1)]


def test_a_read_set_and_a_write_set_do_not_collide():
    assert _res(EnumUsage.READ, "A").compare(_res(EnumUsage.WRITE, "B")) == []


def test_two_read_sets_both_describe_reads():
    (finding,) = _res(EnumUsage.READ, "A").compare(_res(EnumUsage.READ, "B"))
    assert finding.severity is Severity.WARNING
    assert finding.message == "P.R.F: A and B both describe reads"


def test_two_write_sets_both_describe_writes():
    findings = _res(EnumUsage.WRITE, "A").compare(_res(EnumUsage.WRITE, "B"))
    assert _messages(findings) == ["P.R.F: A and B both describe writes"]


def test_a_read_write_set_collides_with_a_read_set_on_reads():
    findings = _res(EnumUsage.READ_WRITE, "the read-write set").compare(
        _res(EnumUsage.READ, "the read set")
    )
    assert _messages(findings) == ["P.R.F: the read-write set and the read set both describe reads"]


def test_a_read_write_set_collides_with_a_write_set_on_writes():
    findings = _res(EnumUsage.READ_WRITE, "A").compare(_res(EnumUsage.WRITE, "B"))
    assert _messages(findings) == ["P.R.F: A and B both describe writes"]


def test_two_read_write_sets_both_describe_reads_and_writes():
    findings = _res(EnumUsage.READ_WRITE, "A").compare(_res(EnumUsage.READ_WRITE, "B"))
    assert _messages(findings) == ["P.R.F: A and B both describe reads and writes"]


def test_a_usage_alone_has_nothing_wrong():
    usage = _res(EnumUsage.READ, "A")
    assert usage.findings() == [] and str(usage) == ""


# --- a usage beside an access ------------------------------------------------------------


def test_a_write_set_beside_a_read_only_access_is_a_warning():
    (finding,) = _res(EnumUsage.WRITE, "the write set").against(Access.READ_ONLY)
    assert finding.severity is Severity.WARNING
    assert finding.message == "P.R.F: the write set describes writes, but access is read-only"


def test_a_read_set_beside_an_access_that_cannot_be_read_is_a_warning():
    for access, spelling in ((Access.WRITE_ONLY, "write-only"), (Access.WRITE_ONCE, "writeOnce")):
        findings = _res(EnumUsage.READ, "the read set").against(access)
        assert _messages(findings) == [
            f"P.R.F: the read set describes reads, but access is {spelling}"
        ]


def test_a_set_beside_an_access_that_allows_it_is_silent():
    assert _res(EnumUsage.READ, "A").against(Access.READ_ONLY) == []
    assert _res(EnumUsage.WRITE, "A").against(Access.WRITE_ONLY) == []
    assert _res(EnumUsage.WRITE, "A").against(Access.READ_WRITE_ONCE) == []


def test_the_default_read_write_set_is_never_reported_against_an_access():
    for access in Access:
        assert _res(EnumUsage.READ_WRITE, "A").against(access) == []


def test_an_access_that_is_unresolved_counts_as_read_write():
    assert _res(EnumUsage.WRITE, "A").against(None) == []


def test_the_usage_class_knows_nothing_above_a_usage():
    source = inspect.getsource(usage_module)
    for above in ("Field", "Register", "Peripheral", "Cluster", "Device", "EnumSet"):
        assert above not in source

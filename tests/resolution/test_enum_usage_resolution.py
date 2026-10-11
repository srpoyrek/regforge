"""EnumUsageResolution: the direction an enumerated set describes, and how it compares."""

import inspect

import regforge.resolution.enum_usage as usage_module
from regforge.finding import Severity
from regforge.ir import EnumUsage
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


def test_the_usage_class_knows_nothing_above_a_usage():
    source = inspect.getsource(usage_module)
    for above in ("Field", "Register", "Peripheral", "Cluster", "Device", "EnumSet"):
        assert above not in source

"""EnumUsage: which direction an enumerated set describes."""

from regforge.ir import EnumUsage


def test_which_usages_cover_reads():
    assert [u for u in EnumUsage if u.covers_read] == [EnumUsage.READ, EnumUsage.READ_WRITE]


def test_which_usages_cover_writes():
    assert [u for u in EnumUsage if u.covers_write] == [EnumUsage.WRITE, EnumUsage.READ_WRITE]

"""Access: the access policy of a register or field, and what it allows."""

from regforge.ir import Access
from regforge.ir.device.access import Access as AccessFromModule


def test_values_are_spelled_as_in_svd():
    assert [a.value for a in Access] == [
        "read-only",
        "write-only",
        "read-write",
        "writeOnce",
        "read-writeOnce",
    ]


def test_which_accesses_can_be_read():
    readable = [a for a in Access if a.can_read]
    assert readable == [Access.READ_ONLY, Access.READ_WRITE, Access.READ_WRITE_ONCE]


def test_which_accesses_can_be_written():
    writable = [a for a in Access if a.can_write]
    assert writable == [
        Access.WRITE_ONLY,
        Access.READ_WRITE,
        Access.WRITE_ONCE,
        Access.READ_WRITE_ONCE,
    ]


def test_it_is_the_same_class_from_the_package_and_from_its_own_module():
    assert AccessFromModule is Access


def test_which_accesses_are_write_once():
    assert [a for a in Access if a.is_write_once] == [Access.WRITE_ONCE, Access.READ_WRITE_ONCE]


def test_which_accesses_can_do_both_directions():
    both = [a for a in Access if a.can_read_and_write]
    assert both == [Access.READ_WRITE, Access.READ_WRITE_ONCE]


def test_write_limit_counts_the_writes_allowed_after_reset():
    assert {a: a.write_limit for a in Access} == {
        Access.READ_ONLY: 0,
        Access.WRITE_ONLY: None,
        Access.READ_WRITE: None,
        Access.WRITE_ONCE: 1,
        Access.READ_WRITE_ONCE: 1,
    }


def test_a_write_once_access_that_can_also_be_read_is_read_write_once():
    assert Access.READ_WRITE_ONCE.can_read and Access.READ_WRITE_ONCE.is_write_once
    assert not Access.WRITE_ONCE.can_read and Access.WRITE_ONCE.is_write_once

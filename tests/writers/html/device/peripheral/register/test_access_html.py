"""AccessHtml: the label the tables show for an access, and the note a write-once one needs."""

import pytest

from regforge.ir import Access
from regforge.writers.html.device.peripheral.register.access import AccessHtml
from regforge.writers.html.wording import NO_VALUE

LABELS = {
    Access.READ_ONLY: "RO",
    Access.WRITE_ONLY: "WO",
    Access.READ_WRITE: "RW",
    Access.WRITE_ONCE: "WO (once)",
    Access.READ_WRITE_ONCE: "RW (write once)",
}


def test_every_access_has_a_label():
    assert set(LABELS) == set(Access)


@pytest.mark.parametrize(("access", "label"), list(LABELS.items()))
def test_each_access_reads_as_its_short_label(access, label):
    assert AccessHtml().label(access) == label


def test_an_unresolved_access_is_an_en_dash():
    assert AccessHtml().label(None) == NO_VALUE


@pytest.mark.parametrize("access", [Access.WRITE_ONCE, Access.READ_WRITE_ONCE])
def test_a_write_once_access_says_so(access):
    assert AccessHtml().note(access) == "can be written only once after reset"


@pytest.mark.parametrize("access", [Access.READ_ONLY, Access.WRITE_ONLY, Access.READ_WRITE, None])
def test_any_other_access_needs_no_note(access):
    assert AccessHtml().note(access) is None

"""ProtectionHtml: what a protection setting requires of an access."""

import pytest

from regforge.ir import Protection
from regforge.writers.html.device.peripheral.register.protection import ProtectionHtml

TEXT = {
    Protection.SECURE: "secure access only",
    Protection.NON_SECURE: "non-secure or secure access",
    Protection.PRIVILEGED: "privileged access only",
}


def test_every_protection_has_its_wording():
    assert set(TEXT) == set(Protection)


@pytest.mark.parametrize(("protection", "text"), list(TEXT.items()))
def test_each_protection_reads_as_what_it_requires(protection, text):
    assert ProtectionHtml().text(protection) == text

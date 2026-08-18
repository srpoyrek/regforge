"""C writer: device identity in the banner and include guard."""

from regforge.ir import Device
from regforge.writers.c import CWriter


def test_identity_shown_in_banner():
    output = CWriter().render(
        Device(name="DemoMCU", vendor="DemoCorp", series="DemoSeries", version="1.0")
    )
    assert "Device:  DemoMCU (DemoCorp, series DemoSeries)" in output
    assert "Version: 1.0" in output
    assert 'DEMOMCU_SVD_VERSION "1.0"' in output


def test_vendor_without_series():
    output = CWriter().render(Device(name="Chip", vendor="Acme"))
    assert "Device:  Chip (Acme)" in output


def test_guard_is_regforge_prefixed():
    assert "#ifndef REGFORGE_CHIP_H" in CWriter().render(Device(name="Chip"))

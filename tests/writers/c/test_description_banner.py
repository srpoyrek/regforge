"""C writer: device description appears in the header banner."""

from regforge.ir import Device
from regforge.writers.c import CWriter


def test_description_shown_in_banner():
    output = CWriter().render(Device(name="Chip", description="A tiny test chip"))
    assert "A tiny test chip" in output


def test_missing_description_is_omitted():
    output = CWriter().render(Device(name="Chip"))
    assert "#ifndef REGFORGE_CHIP_H" in output  # still renders cleanly
    assert "Chip register definitions." in output
    assert "None" not in output  # no stray placeholder for the absent description

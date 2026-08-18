"""C writer: source license copied, generated output declared license-free."""

from regforge.ir import Device
from regforge.writers.c import CWriter


def test_license_copied_and_output_marked_cc0():
    output = CWriter().render(Device(name="Chip", license_text="Copyright X\nApache-2.0"))
    assert "Copyright X" in output  # source license copied verbatim
    assert "Apache-2.0" in output
    assert "CC0-1.0" in output  # generated output declared license-free


def test_no_license_means_no_cc0_statement():
    output = CWriter().render(Device(name="Chip"))
    assert "CC0" not in output
    assert "Source license" not in output

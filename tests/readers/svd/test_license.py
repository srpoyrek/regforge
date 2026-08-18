"""Layer 1 device license: licenseText extraction."""


def test_reads_license_text(demo_device):
    assert demo_device.license_text is not None
    assert "Apache License" in demo_device.license_text
    # Outer whitespace stripped; internal line breaks preserved.
    assert demo_device.license_text.startswith("Copyright (c) 2024 DemoCorp.")
    assert "\n" in demo_device.license_text

"""Layer 1 device identity: vendor / name / series / version."""


def test_reads_device_identity(demo_device):
    assert demo_device.name == "DemoMCU"
    assert demo_device.vendor == "DemoCorp"
    assert demo_device.series == "DemoSeries"
    assert demo_device.version == "1.0"

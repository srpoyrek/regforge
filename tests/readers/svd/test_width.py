"""Layer 1 device `<width>` (bus width) parsing.

Register-size *resolution* (which uses the bus width as a fallback) is exercised
in tests/resolve/, since it happens in the defaults pass, not the reader.
"""

from regforge.readers.svd import SvdReader


def test_reads_bus_width(demo_device):
    assert demo_device.bus_width == 32


def test_bus_width_defaults_to_32(tmp_path):
    svd = tmp_path / "nowidth.svd"
    svd.write_text("<device><name>X</name></device>", encoding="utf-8")
    assert SvdReader().read(svd).bus_width == 32


def test_bus_width_explicit(tmp_path):
    svd = tmp_path / "w64.svd"
    svd.write_text("<device><name>X</name><width>64</width></device>", encoding="utf-8")
    assert SvdReader().read(svd).bus_width == 64

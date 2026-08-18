"""Layer 1 device description extraction."""

from regforge.readers.svd import SvdReader


def test_reads_description(demo_device):
    assert demo_device.description == "Minimal demo device used by the regforge test suite"


def test_description_is_optional(tmp_path):
    # Not every vendor SVD includes <description>; absence must be graceful.
    svd = tmp_path / "nodesc.svd"
    svd.write_text("<device><name>NoDesc</name></device>", encoding="utf-8")
    device = SvdReader().read(svd)
    assert device.description is None

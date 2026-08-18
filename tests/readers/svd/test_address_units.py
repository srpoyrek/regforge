"""Layer 1 device `addressUnitBits` extraction."""

from regforge.readers.svd import SvdReader


def test_reads_address_unit_bits(demo_device):
    assert demo_device.address_unit_bits == 8


def test_defaults_to_8_when_absent(tmp_path):
    svd = tmp_path / "nounits.svd"
    svd.write_text("<device><name>X</name></device>", encoding="utf-8")
    assert SvdReader().read(svd).address_unit_bits == 8


def test_reads_word_addressable_value(tmp_path):
    svd = tmp_path / "word.svd"
    svd.write_text(
        "<device><name>X</name><addressUnitBits>16</addressUnitBits></device>",
        encoding="utf-8",
    )
    assert SvdReader().read(svd).address_unit_bits == 16

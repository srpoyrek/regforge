"""Layer 1 device `<cpu>` block: extraction and boolean normalization."""

import pytest

from regforge.readers.svd import SvdReader, parse_svd_bool


def test_reads_cpu_fields(demo_device):
    cpu = demo_device.cpu
    assert cpu is not None
    assert cpu.name == "CM0PLUS"
    assert cpu.revision == "r0p1"
    assert cpu.endian == "little"
    assert cpu.mpu_present is True
    assert cpu.fpu_present is False
    assert cpu.vtor_present is True  # normalized from "1"
    assert cpu.nvic_prio_bits == 2
    assert cpu.vendor_systick is False
    assert cpu.num_interrupts == 32


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("true", True),
        ("false", False),
        ("1", True),
        ("0", False),
        ("TRUE", True),
        (" 0 ", False),
        ("maybe", None),
    ],
)
def test_boolean_normalization(text, expected):
    assert parse_svd_bool(text) == expected


def test_cpu_is_optional(tmp_path):
    svd = tmp_path / "nocpu.svd"
    svd.write_text("<device><name>NoCpu</name></device>", encoding="utf-8")
    assert SvdReader().read(svd).cpu is None


def test_absent_cpu_fields_are_none(tmp_path):
    # Missing fields stay None; the reader never guesses (e.g. the F411 lie).
    svd = tmp_path / "partial.svd"
    svd.write_text("<device><name>P</name><cpu><name>CM4</name></cpu></device>", encoding="utf-8")
    cpu = SvdReader().read(svd).cpu
    assert cpu.name == "CM4"
    assert cpu.fpu_present is None
    assert cpu.nvic_prio_bits is None

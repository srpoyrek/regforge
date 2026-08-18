"""Layer 1 device `<width>` (bus width) and register-size resolution."""

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


def test_register_size_falls_back_to_bus_width(tmp_path):
    # No register <size>, no device <size> -> inherit device <width>.
    svd = tmp_path / "r.svd"
    svd.write_text(
        "<device><name>X</name><width>16</width><peripherals><peripheral>"
        "<name>P</name><baseAddress>0x0</baseAddress><registers><register>"
        "<name>R</name><addressOffset>0x0</addressOffset></register>"
        "</registers></peripheral></peripherals></device>",
        encoding="utf-8",
    )
    register = SvdReader().read(svd).peripherals[0].registers[0]
    assert register.size == 16


def test_register_size_resolution_order(tmp_path):
    # Device <size> beats <width>; a register's own <size> beats device <size>.
    svd = tmp_path / "r.svd"
    svd.write_text(
        "<device><name>X</name><width>32</width><size>16</size><peripherals>"
        "<peripheral><name>P</name><baseAddress>0x0</baseAddress><registers>"
        "<register><name>R1</name><addressOffset>0x0</addressOffset></register>"
        "<register><name>R2</name><addressOffset>0x2</addressOffset><size>8</size></register>"
        "</registers></peripheral></peripherals></device>",
        encoding="utf-8",
    )
    registers = SvdReader().read(svd).peripherals[0].registers
    assert registers[0].size == 16  # inherits device <size>
    assert registers[1].size == 8  # own <size> wins

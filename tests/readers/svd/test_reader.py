"""SvdReader: opens a file and starts the parsers at the device."""

from regforge.readers.svd import SvdReader


def test_the_reader_names_its_format_and_extension():
    assert SvdReader.format_name == "svd"
    assert SvdReader.file_extensions == (".svd",)


def test_it_reads_a_file_into_a_device(tmp_path):
    svd = tmp_path / "d.svd"
    svd.write_text("<device><name>D</name></device>", encoding="utf-8")
    assert SvdReader().read(svd).name == "D"


def test_what_the_parsers_note_lands_on_the_readers_warnings(tmp_path):
    svd = tmp_path / "d.svd"
    svd.write_text(
        "<device><name>D</name><peripherals><peripheral><name>P%s</name>"
        "<baseAddress>0x0</baseAddress><dim>2</dim><dimIncrement>0x10</dimIncrement>"
        "<dimIndex>1-0</dimIndex></peripheral></peripherals></device>",
        encoding="utf-8",
    )
    reader = SvdReader()
    reader.read(svd)
    assert len(reader.warnings) == 1 and "reversed" in reader.warnings[0]


def test_each_read_starts_with_fresh_warnings(tmp_path):
    svd = tmp_path / "d.svd"
    svd.write_text(
        "<device><name>D</name><peripherals><peripheral><name>P%s</name>"
        "<baseAddress>0x0</baseAddress><dim>2</dim><dimIncrement>0x10</dimIncrement>"
        "<dimIndex>1-0</dimIndex></peripheral></peripherals></device>",
        encoding="utf-8",
    )
    reader = SvdReader()
    reader.read(svd)
    reader.read(svd)
    assert len(reader.warnings) == 1

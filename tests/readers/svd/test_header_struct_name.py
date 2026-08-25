"""Reading <headerStructName>, and how it combines with <groupName>."""

from regforge.readers.svd import SvdReader

_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<device schemaVersion="1.3">
  <name>D</name><addressUnitBits>8</addressUnitBits><width>32</width>
  <size>32</size><access>read-write</access>
  <peripherals>
    <peripheral>
      <name>P0</name>
      <baseAddress>0x0</baseAddress>
{elements}
      <registers>
        <register><name>R</name><addressOffset>0x0</addressOffset></register>
      </registers>
    </peripheral>
  </peripherals>
</device>
"""


def _read(tmp_path, elements):
    path = tmp_path / "d.svd"
    path.write_text(_TEMPLATE.format(elements=elements), encoding="utf-8")
    return SvdReader().read(path).peripherals[0]


def test_both_absent(tmp_path):
    peripheral = _read(tmp_path, "")
    assert peripheral.group_name is None
    assert peripheral.header_struct_name is None


def test_group_name_only(tmp_path):
    peripheral = _read(tmp_path, "      <groupName>GRP</groupName>")
    assert peripheral.group_name == "GRP"
    assert peripheral.header_struct_name is None


def test_header_struct_name_only(tmp_path):
    peripheral = _read(tmp_path, "      <headerStructName>HSN</headerStructName>")
    assert peripheral.group_name is None
    assert peripheral.header_struct_name == "HSN"


def test_both_present(tmp_path):
    peripheral = _read(
        tmp_path,
        "      <groupName>GRP</groupName>\n" "      <headerStructName>HSN</headerStructName>",
    )
    assert peripheral.group_name == "GRP"
    assert peripheral.header_struct_name == "HSN"


def test_empty_element_reads_as_none(tmp_path):
    # <headerStructName/> carries no text at all -- absent, not an empty name.
    peripheral = _read(tmp_path, "      <headerStructName></headerStructName>")
    assert peripheral.header_struct_name is None


def test_whitespace_is_stripped(tmp_path):
    # Vendors pretty-print; the surrounding whitespace is not part of the name.
    peripheral = _read(tmp_path, "      <headerStructName>\n        HSN\n      </headerStructName>")
    assert peripheral.header_struct_name == "HSN"


def test_whitespace_only_reads_as_empty_and_never_names_a_type(tmp_path):
    # Stripped to "", which is falsy, so the precedence falls through to the
    # next rung rather than emitting a type named after blank space.
    peripheral = _read(tmp_path, "      <headerStructName>   </headerStructName>")
    assert peripheral.header_struct_name == ""

"""SVD reader: alternateRegister and alternateGroup land on the register as declared."""

from regforge.readers.svd import SvdReader

_SVD = """<?xml version="1.0" encoding="utf-8"?>
<device schemaVersion="1.3">
  <name>Chip</name><addressUnitBits>8</addressUnitBits><width>32</width><size>32</size>
  <peripherals>
    <peripheral>
      <name>TIM</name><baseAddress>0x40000000</baseAddress>
      <registers>
        <register><name>CCMR1_Output</name><addressOffset>0x18</addressOffset></register>
        <register>
          <name>CCMR1_Input</name><alternateRegister>CCMR1_Output</alternateRegister>
          <addressOffset>0x18</addressOffset>
        </register>
        <register><name>DR</name><addressOffset>0x20</addressOffset></register>
        <register><name>DR</name><alternateGroup>Cal</alternateGroup><addressOffset>0x20</addressOffset></register>
        <register>
          <name>DR</name><alternateGroup>Raw</alternateGroup><alternateRegister>DR</alternateRegister>
          <addressOffset>0x20</addressOffset>
        </register>
      </registers>
    </peripheral>
  </peripherals>
</device>
"""


def _sets(tmp_path):
    path = tmp_path / "alt.svd"
    path.write_text(_SVD, encoding="utf-8")
    return SvdReader().read(path).peripherals[0].alternate_sets


def _registers(tmp_path):
    return [view for alternate_set in _sets(tmp_path) for view in alternate_set.views]


def test_every_register_is_read_as_a_set_of_one_view(tmp_path):
    sets = _sets(tmp_path)
    assert [s.names for s in sets] == [("CCMR1_Output",), ("CCMR1_Input",)] + [("DR",)] * 3
    assert not any(s.is_alternate for s in sets)  # merged by the resolve pass, not here


def test_alternate_register_is_read_as_declared(tmp_path):
    joins = {s.primary.name: s.joins for s in _sets(tmp_path)}
    assert joins["CCMR1_Output"] is None
    assert joins["CCMR1_Input"] == "CCMR1_Output"


def test_alternate_group_is_a_label_the_reader_neither_renames_nor_links(tmp_path):
    plain, cal, raw = _registers(tmp_path)[2:]
    assert [r.name for r in (plain, cal, raw)] == ["DR", "DR", "DR"]
    assert [r.alternate_group for r in (plain, cal, raw)] == [None, "Cal", "Raw"]
    # Only what the file wrote is a link: an explicit alternateRegister beside the group.
    assert [s.joins for s in _sets(tmp_path)[2:]] == [None, None, "DR"]

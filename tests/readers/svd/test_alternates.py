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


def _registers(tmp_path):
    path = tmp_path / "alt.svd"
    path.write_text(_SVD, encoding="utf-8")
    return {r.name: r for r in SvdReader().read(path).peripherals[0].registers}


def test_alternate_register_is_read_as_declared(tmp_path):
    registers = _registers(tmp_path)
    assert registers["CCMR1_Output"].alternate_register is None
    assert registers["CCMR1_Input"].alternate_register == "CCMR1_Output"
    assert registers["CCMR1_Input"].alternates == ()  # linked by the resolve pass, not here


def test_alternate_group_renames_the_view_and_links_it_to_the_plain_register(tmp_path):
    registers = _registers(tmp_path)
    assert "DR_Cal" in registers and registers["DR_Cal"].alternate_register == "DR"
    # An explicit alternateRegister beside the group is kept as written.
    assert registers["DR_Raw"].alternate_register == "DR"
    assert registers["DR"].alternate_register is None

"""AlternateSetResolution: whether a declared alternate may join that word."""

from regforge.finding import Severity
from regforge.ir import Dim, Register
from regforge.resolution.device.peripheral.alternate_set import AlternateSetResolution


def _rules(register, wanted, candidates, where="SPI0"):
    return AlternateSetResolution(register, wanted, candidates, where)


def test_a_name_in_the_block_is_the_target():
    dr = Register("DR", 0x4)
    rxd = Register("RXD", 0x4)
    rules = _rules(rxd, "DR", [dr, rxd])
    assert rules.target() is dr and rules.findings() == []


def test_a_name_no_register_carries_is_an_error():
    rxd = Register("RXD", 0x4)
    rules = _rules(rxd, "MISSING", [rxd])
    (finding,) = rules.findings()
    assert rules.target() is None
    assert finding.severity is Severity.ERROR
    assert "no register of that name in SPI0" in finding.message


def test_a_view_naming_itself_is_ignored():
    rxd = Register("RXD", 0x4)
    rules = _rules(rxd, "RXD", [rxd])
    (finding,) = rules.findings()
    assert rules.target() is None
    assert finding.severity is Severity.WARNING and "names itself" in finding.message


def test_a_target_at_another_offset_is_left_unrelated():
    dr = Register("DR", 0x8)
    rxd = Register("RXD", 0x4)
    rules = _rules(rxd, "DR", [dr, rxd])
    (finding,) = rules.findings()
    assert rules.target() is None
    assert "is at offset 0x8, not 0x4" in finding.message


def test_a_target_of_another_shape_is_left_unrelated():
    dr = Register("DR", 0x4, dim=Dim(4, 4))
    rxd = Register("RXD", 0x4)
    rules = _rules(rxd, "DR", [dr, rxd])
    (finding,) = rules.findings()
    assert rules.target() is None
    assert "different <dim> shape" in finding.message


def test_an_array_name_matches_the_array_it_was_kept_as():
    cc = Register("CC", 0x10, dim=Dim(4, 4, array=True))
    cci = Register("CCI", 0x10, dim=Dim(4, 4, array=True))
    rules = _rules(cci, "CC[%s]", [cc, cci])
    assert rules.target() is cc and rules.findings() == []


def test_naming_a_template_resolves_to_its_first_copy_with_a_warning():
    dt0 = Register("DT0", 0x20, expanded_from="DT%s")
    dt1 = Register("DT1", 0x24, expanded_from="DT%s")
    plain = Register("PLAIN", 0x20)
    rules = _rules(plain, "DT%s", [dt0, dt1, plain])
    (finding,) = rules.findings()
    assert rules.target() is dt0
    assert "names the template 'DT%s'" in finding.message and "DT0" in finding.message


def test_a_copy_pairs_with_the_copy_of_the_same_index():
    dt0 = Register("DT0", 0x20, expanded_from="DT%s")
    dt1 = Register("DT1", 0x24, expanded_from="DT%s")
    dtr0 = Register("DTR0", 0x20, expanded_from="DTR%s")
    dtr1 = Register("DTR1", 0x24, expanded_from="DTR%s")
    candidates = [dt0, dt1, dtr0, dtr1]
    assert _rules(dtr1, "DT%s", candidates).target() is dt1
    assert _rules(dtr0, "DT%s", candidates).findings() == []


def test_a_different_copy_count_leaves_the_pair_unrelated():
    dt0 = Register("DT0", 0x20, expanded_from="DT%s")
    dtr0 = Register("DTR0", 0x20, expanded_from="DTR%s")
    dtr1 = Register("DTR1", 0x24, expanded_from="DTR%s")
    rules = _rules(dtr0, "DT%s", [dt0, dtr0, dtr1])
    (finding,) = rules.findings()
    assert rules.target() is None
    assert "expands to 1 copies, not 2" in finding.message


def test_a_copy_count_mismatch_reports_only_that():
    dt0 = Register("DT0", 0x20, expanded_from="DT%s")
    dtr0 = Register("DTR0", 0x20, expanded_from="DTR%s")
    dtr1 = Register("DTR1", 0x24, expanded_from="DTR%s")
    assert len(_rules(dtr0, "DT%s", [dt0, dtr0, dtr1]).findings()) == 1


def test_same_shape_pairs_two_plain_registers_and_two_matching_arrays():
    plain = Register("A", 0x0)
    other = Register("B", 0x0)
    array = Register("C", 0x0, dim=Dim(4, 4))
    wider = Register("D", 0x0, dim=Dim(8, 4))
    assert AlternateSetResolution.same_shape(plain, other)
    assert AlternateSetResolution.same_shape(array, Register("E", 0x0, dim=Dim(4, 4)))
    assert not AlternateSetResolution.same_shape(plain, array)
    assert not AlternateSetResolution.same_shape(array, wider)


def test_the_label_names_the_block_and_the_register():
    rxd = Register("RXD", 0x4)
    assert _rules(rxd, "DR", [rxd]).label == "SPI0.RXD"


def test_str_is_the_report_and_is_empty_when_nothing_is_wrong():
    dr = Register("DR", 0x4)
    rxd = Register("RXD", 0x4)
    assert str(_rules(rxd, "DR", [dr, rxd])) == ""
    assert "names itself" in str(_rules(rxd, "RXD", [rxd]))

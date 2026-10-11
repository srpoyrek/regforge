"""AlternateSet: registers that are different views of one word, like a C union."""

import pytest

from regforge.ir import AlternateSet, Field, Register, alternate_sets


def _crc() -> list[Register]:
    # One word seen three ways, like a CRC data register: 32, 8 and 16 bits wide.
    views = [
        Register("DR", 0x0, size=32, fields=[Field("DATA", 0, 32)]),
        Register("DR8", 0x0, size=8, fields=[Field("BYTE", 0, 8)]),
        Register("DR16", 0x0, size=16, fields=[Field("HALF", 0, 16)]),
    ]
    names = tuple(view.name for view in views)
    for view in views:
        view.alternates = names  # what resolve_alternates does
    return views


def test_the_primary_is_the_first_view_and_the_offset_is_shared():
    views = _crc()
    union = AlternateSet(tuple(views))
    assert union.primary is views[0]
    assert union.address_offset == 0x0


def test_the_word_is_as_wide_as_its_widest_view():
    assert AlternateSet(tuple(_crc())).width == 32


def test_view_named_finds_a_view_or_none():
    union = AlternateSet(tuple(_crc()))
    assert union.view_named("DR16") is union.views[2]
    assert union.view_named("NOPE") is None


def test_owners_names_the_field_each_view_puts_on_a_bit():
    union = AlternateSet(tuple(_crc()))

    def names(position):
        return {
            view: field.name if field else None for view, field in union.owners(position).items()
        }

    assert names(3) == {"DR": "DATA", "DR8": "BYTE", "DR16": "HALF"}
    assert names(12) == {"DR": "DATA", "DR8": None, "DR16": "HALF"}  # past the 8-bit view
    assert names(20) == {"DR": "DATA", "DR8": None, "DR16": None}  # past the 16-bit view


def test_a_write_through_one_view_is_seen_by_the_others():
    union = AlternateSet(tuple(_crc()))
    word = union.write(0xFFFF0000, "DR8", "BYTE", 0x5A)
    assert word == 0xFFFF005A
    assert union.read(word, "DR16", "HALF") == 0x005A
    assert union.read(word, "DR", "DATA") == 0xFFFF005A


def test_a_value_that_does_not_fit_the_view_is_refused():
    with pytest.raises(ValueError, match="BYTE"):
        AlternateSet(tuple(_crc())).write(0, "DR8", "BYTE", 0x100)


def test_an_unknown_view_or_field_is_refused():
    union = AlternateSet(tuple(_crc()))
    with pytest.raises(KeyError, match="NOPE"):
        union.read(0, "NOPE", "BYTE")
    with pytest.raises(KeyError, match="NOPE"):
        union.read(0, "DR8", "NOPE")


def test_an_empty_set_is_refused():
    with pytest.raises(ValueError, match="at least one view"):
        AlternateSet(())


def test_the_width_refuses_a_view_with_an_unresolved_size():
    with pytest.raises(ValueError, match="unresolved"):
        _ = AlternateSet((Register("A", 0x0),)).width


def test_alternate_sets_groups_linked_registers_in_the_order_their_primaries_appear():
    lone = Register("LONE", 0x40, size=32)
    first = _crc()
    second = [Register("CC", 0x10, size=32), Register("CCI", 0x10, size=32)]
    for view in second:
        view.alternates = ("CC", "CCI")
    found = alternate_sets([*first, lone, *second])
    assert [[v.name for v in s.views] for s in found] == [["DR", "DR8", "DR16"], ["CC", "CCI"]]


def test_a_lone_register_belongs_to_no_set():
    assert alternate_sets([Register("LONE", 0x0, size=32)]) == []


def test_the_fixtures_crc_data_register_is_one_word_seen_three_ways(demo_device):
    crc = next(p for p in demo_device.peripherals if p.name == "CRC")
    (union,) = alternate_sets(crc.registers)
    assert [v.name for v in union.views] == ["DR", "DR8", "DR16"]
    assert union.width == 32


def test_the_fixtures_pwm_has_three_sets(demo_device):
    pwma = next(p for p in demo_device.peripherals if p.name == "PWMA")
    assert [s.primary.name for s in alternate_sets(pwma.registers)] == ["CC", "DT0", "DT1"]


def test_names_lists_the_views_primary_first():
    assert AlternateSet(tuple(_crc())).names == ("DR", "DR8", "DR16")

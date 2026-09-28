"""Layout: declared views of one word become one union slot; undeclared overlap is refused."""

import pytest

from regforge.ir import Cluster, Device, Dim, Peripheral, Register
from regforge.layout import LayoutError, peripheral_layout, union_naming
from regforge.resolve import expand_dim, resolve_alternates


def _laid_out(*registers: Register, clusters: list[Cluster] | None = None):
    peripheral = Peripheral("P", 0x0, registers=list(registers), clusters=list(clusters or []))
    device = Device(name="Chip", peripherals=[peripheral])
    expand_dim(device)
    resolve_alternates(device)
    return peripheral_layout(peripheral, address_unit_bits=8)


def test_union_slot_is_as_wide_as_its_widest_view():
    dr, dr8, dr16 = (
        Register("DR", 0x0, size=32),
        Register("DR8", 0x0, size=8, alternate_register="DR"),
        Register("DR16", 0x0, size=16, alternate_register="DR"),
    )
    (slot,) = _laid_out(dr, dr8, dr16)
    assert slot.views == (dr, dr8, dr16) and slot.union == "DR"
    assert slot.view_names == ("DR", "DR8", "DR16")  # rule 2: 8 and 16 are not identifiers
    assert (slot.offset, slot.element_bytes, slot.size_bytes, slot.count) == (0, 4, 4, 1)
    assert not slot.is_reserved and slot.label == "DR"


def test_common_prefix_names_the_union_and_the_views_keep_their_remainders():
    (slot,) = _laid_out(
        Register("CCMR1_Output", 0x0, size=32),
        Register("CCMR1_Input", 0x0, size=32, alternate_register="CCMR1_Output"),
    )
    assert slot.union == "CCMR1" and slot.view_names == ("Output", "Input")


def test_prefix_used_by_a_sibling_falls_back_to_the_primary_name():
    ccr, x, y = (
        Register("CCR", 0x0, size=32),
        Register("CCR_X", 0x4, size=32),
        Register("CCR_Y", 0x4, size=32, alternate_register="CCR_X"),
    )
    _, slot = _laid_out(ccr, x, y)
    assert slot.union == "CCR_X" and slot.view_names == ("CCR_X", "CCR_Y")


def test_union_naming_reports_only_the_sibling_collision():
    views = [Register("CCR_X", 0x4, size=32), Register("CCR_Y", 0x4, size=32)]
    assert union_naming(views, set()) == ("CCR", ("X", "Y"), None)
    name, members, reason = union_naming(views, {"CCR"})
    assert (name, members) == ("CCR_X", ("CCR_X", "CCR_Y"))
    assert reason == "the common prefix 'CCR' is already a member of the block"
    # No usable prefix at all is silent: nothing was blocked.
    assert union_naming([Register("DR", 0, size=32), Register("TXD", 0, size=32)], set()) == (
        "DR",
        ("DR", "TXD"),
        None,
    )


def test_undeclared_overlap_is_still_refused_with_the_alternate_hint():
    with pytest.raises(
        LayoutError, match=r"P\.B: register at offset 0x0 overlaps.*alternateRegister"
    ):
        _laid_out(Register("A", 0x0, size=32), Register("B", 0x0, size=32))


def test_packed_union_array_is_one_slot():
    (slot,) = _laid_out(
        Register("CC[%s]", 0x0, size=32, dim=Dim(4, 4)),
        Register("CCI[%s]", 0x0, size=32, dim=Dim(4, 4), alternate_register="CC[%s]"),
    )
    assert slot.union == "CC" and slot.count == 4 and slot.size_bytes == 16


def test_unpacked_union_array_is_one_slot_per_element():
    slots = _laid_out(
        Register("CC[%s]", 0x0, size=32, dim=Dim(2, 8)),
        Register("CCI[%s]", 0x0, size=32, dim=Dim(2, 8), alternate_register="CC[%s]"),
    )
    named = [(s.offset, s.name, s.index, s.union) for s in slots if s.views]
    assert named == [(0x0, "CC0", 0, "CC"), (0x8, "CC1", 1, "CC")]
    assert [s.gap_bytes for s in slots if s.is_reserved] == [4]  # the hole after CC0


def test_union_array_with_a_stride_narrower_than_a_view_is_refused():
    with pytest.raises(LayoutError, match=r"P\.CC\[2\]: stride 2 byte\(s\) is smaller"):
        _laid_out(
            Register("CC[%s]", 0x0, size=32, dim=Dim(2, 2)),
            Register("CCI[%s]", 0x0, size=32, dim=Dim(2, 2), alternate_register="CC[%s]"),
        )


def test_union_inside_a_cluster_fills_the_element():
    cluster = Cluster(
        "CH",
        0x10,
        dim=Dim(2, 0x8),
        registers=[
            Register("CTRL", 0x0, size=32),
            Register("XFER_Mem", 0x4, size=32),
            Register("XFER_Periph", 0x4, size=32, alternate_register="XFER_Mem"),
        ],
    )
    ch = _laid_out(Register("CFG", 0x0, size=32), clusters=[cluster])[-1]
    assert [m.union for m in ch.members] == [None, "XFER"]
    assert ch.element_bytes == 8 and not any(m.is_reserved for m in ch.members)

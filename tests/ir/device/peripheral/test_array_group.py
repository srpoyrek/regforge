"""ArrayGroup: the compact reading of one declared array whose copies were unrolled."""

from regforge.ir import ArrayGroup, Dim, DimOrigin, Register, array_groups, compact


def _copies(template, count, step, base):
    dim = Dim(count, step)
    stem = template.replace("%s", "")
    return [
        Register(f"{stem}{i}", base + i * step, origin=DimOrigin(template, dim, i, str(i)))
        for i in range(count)
    ]


def test_array_groups_collects_the_copies_of_one_template():
    lone = Register("CC", 0x10)
    dt = _copies("DT%s", 2, 8, 0x20)
    (group,) = array_groups([lone, *dt])
    assert group.template == "DT%s"
    assert group.names == ("DT0", "DT1")
    assert group.count == 2


def test_a_group_carries_the_original_recipe():
    (group,) = array_groups(_copies("DT%s", 2, 8, 0x20))
    assert (group.dim.count, group.dim.increment) == (2, 8)


def test_elements_without_an_origin_form_no_group():
    assert array_groups([Register("A", 0x0), Register("B", 0x4)]) == []


def test_two_templates_make_two_groups_in_the_order_they_first_appear():
    elements = [*_copies("DT%s", 2, 8, 0x20), *_copies("DTR%s", 2, 8, 0x20)]
    assert [g.template for g in array_groups(elements)] == ["DT%s", "DTR%s"]


def test_compact_puts_one_group_where_the_first_copy_was():
    lone = Register("CC", 0x10)
    after = Register("ZZ", 0x80)
    result = compact([lone, *_copies("DT%s", 2, 8, 0x20), after])
    assert len(result) == 3
    assert result[0] is lone and result[2] is after
    assert isinstance(result[1], ArrayGroup) and result[1].names == ("DT0", "DT1")


def test_compact_leaves_a_list_with_no_arrays_unchanged():
    elements = [Register("A", 0x0), Register("B", 0x4)]
    assert compact(elements) == elements

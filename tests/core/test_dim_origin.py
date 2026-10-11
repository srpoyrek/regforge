"""DimOrigin: where an unrolled copy came from."""

from regforge.ir import Dim, DimOrigin


def test_it_remembers_the_template_the_recipe_and_the_copys_place():
    dim = Dim(4, 4)
    origin = DimOrigin("DATA%s", dim, 2, "2")
    assert (origin.template, origin.index, origin.label) == ("DATA%s", 2, "2")
    assert origin.dim is dim


def test_count_and_offset_follow_the_recipe():
    origin = DimOrigin("DATA%s", Dim(4, 4), 2, "2")
    assert origin.count == 4
    assert origin.offset == 8


def test_first_and_last_copy():
    dim = Dim(3, 4)
    assert DimOrigin("D%s", dim, 0, "0").is_first
    assert not DimOrigin("D%s", dim, 1, "1").is_first
    assert DimOrigin("D%s", dim, 2, "2").is_last
    assert not DimOrigin("D%s", dim, 1, "1").is_last

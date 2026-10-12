"""Dim: an array of copies, ``count`` of them ``increment`` apart."""

import pytest

from regforge.ir import Dim, EnumeratedValue
from regforge.ir.device.peripheral.dim import Dim as DimFromModule


def test_labels_default_to_numbers_from_zero():
    assert Dim(3, 4).labels == ["0", "1", "2"]


def test_labels_use_dimindex_when_given():
    assert Dim(3, 4, index=["A", "B", "C"]).labels == ["A", "B", "C"]


def test_length_and_stride_read_the_count_and_increment():
    dim = Dim(8, 4)
    assert (dim.length, dim.stride) == (8, 4)


def test_a_fresh_dim_is_undecided_until_expansion_sets_array():
    dim = Dim(2, 4)
    assert dim.array is False and dim.name is None and dim.array_index == []


def test_array_index_names_are_kept_in_order():
    dim = Dim(2, 4, array_index=[EnumeratedValue("LOW", 0), EnumeratedValue("HIGH", 1)])
    assert [e.name for e in dim.array_index] == ["LOW", "HIGH"]


def test_offsets_are_each_copys_distance_from_the_first():
    assert Dim(4, 0x10).offsets == [0x0, 0x10, 0x20, 0x30]


def test_offset_of_and_label_of_find_a_copy():
    dim = Dim(3, 4, index=["A", "B", "C"])
    assert dim.offset_of(2) == 8
    assert dim.label_of(2) == "C"


def test_a_copy_outside_the_array_is_refused():
    with pytest.raises(IndexError, match="outside"):
        Dim(3, 4).offset_of(3)
    with pytest.raises(IndexError, match="outside"):
        Dim(3, 4).label_of(-1)


def test_copy_of_finds_the_copy_for_a_label():
    dim = Dim(3, 4, index=["A", "B", "C"])
    assert dim.copy_of("B") == 1
    assert dim.copy_of("Z") is None


def test_extent_is_the_span_to_the_end_of_the_last_copy():
    assert Dim(4, 0x10).extent(8) == 0x30 + 8


def test_copies_overlap_when_the_stride_is_smaller_than_an_element():
    assert Dim(4, 4).copies_overlap(8)
    assert not Dim(4, 8).copies_overlap(8)
    assert not Dim(1, 1).copies_overlap(8)  # one copy has no neighbour


def test_it_is_the_same_class_from_the_package_and_from_its_own_module():
    assert DimFromModule is Dim

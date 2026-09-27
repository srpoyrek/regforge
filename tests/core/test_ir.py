"""Core intermediate representation."""

from regforge.ir import Cluster, Dim, Field


def test_field_mask_is_positioned():
    assert Field("A", bit_offset=0, bit_width=2).mask == 0x3
    assert Field("B", bit_offset=2, bit_width=2).mask == 0xC
    assert Field("C", bit_offset=8, bit_width=8).mask == 0xFF00


def test_field_full_width_mask():
    assert Field("D", bit_offset=0, bit_width=32).mask == 0xFFFFFFFF


def test_dim_labels_default_to_numbers():
    assert Dim(count=4, increment=0x400).labels == ["0", "1", "2", "3"]


def test_dim_labels_use_the_given_index():
    dim = Dim(count=3, increment=0x1000, index=["A", "B", "C"])
    assert dim.labels == ["A", "B", "C"]


def test_cluster_starts_empty():
    cluster = Cluster(name="CH", address_offset=0x10)
    assert cluster.registers == [] and cluster.clusters == [] and cluster.dim is None

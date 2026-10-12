"""Cluster: a named group of registers inside a peripheral, and the walk over nested ones."""

from regforge.ir import Cluster, walk_clusters


def test_a_cluster_starts_empty():
    cluster = Cluster(name="CH", address_offset=0x10)
    assert cluster.registers == [] and cluster.clusters == [] and cluster.dim is None


def test_a_cluster_keeps_its_offset_and_what_it_is_called():
    cluster = Cluster("CH", 0x10, header_struct_name="ch_t")
    assert (cluster.name, cluster.address_offset, cluster.header_struct_name) == (
        "CH",
        0x10,
        "ch_t",
    )


def test_walk_clusters_names_each_cluster_by_its_dotted_path_depth_first():
    inner = Cluster("SUB", 0x20)
    outer = Cluster("CH", 0x10, clusters=[inner])
    other = Cluster("TWO", 0x40)
    walked = [(path, cluster.name) for path, cluster in walk_clusters([outer, other], "DMA")]
    assert walked == [("DMA.CH", "CH"), ("DMA.CH.SUB", "SUB"), ("DMA.TWO", "TWO")]


def test_walking_no_clusters_gives_nothing():
    assert list(walk_clusters([], "DMA")) == []

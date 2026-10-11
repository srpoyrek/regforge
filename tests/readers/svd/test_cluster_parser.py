"""ClusterParser: reads a <cluster> element."""

import xml.etree.ElementTree as ET

from regforge.ir import (
    Protection,
)
from regforge.readers.svd.cluster import ClusterParser
from regforge.readers.svd.element_parser import ParseContext


def _el(xml: str) -> ET.Element:
    return ET.fromstring(xml)


def test_a_cluster_nests_registers_and_clusters():
    cluster = ClusterParser(ParseContext()).parse(
        _el(
            "<cluster derivedFrom='BASE'><name>CH</name><addressOffset>0x10</addressOffset>"
            "<headerStructName>ch_t</headerStructName><protection>p</protection>"
            "<register><name>CTRL</name><addressOffset>0x0</addressOffset></register>"
            "<cluster><name>SUB</name><addressOffset>0x20</addressOffset></cluster></cluster>"
        )
    )
    assert (cluster.name, cluster.address_offset, cluster.header_struct_name) == ("CH", 16, "ch_t")
    assert cluster.derived_from == "BASE" and cluster.default_protection is Protection.PRIVILEGED
    assert [r.name for r in cluster.registers] == ["CTRL"]
    assert [c.name for c in cluster.clusters] == ["SUB"]

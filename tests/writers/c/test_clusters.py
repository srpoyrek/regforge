"""C writer: clusters as nested struct types, single or as arrays."""

import re

import pytest

from regforge.ir import Access, Cluster, Device, Dim, Field, Peripheral, Register
from regforge.resolve import expand_dim, resolve_defaults, resolve_derived
from regforge.writers.base import EmitError
from regforge.writers.c import CWriter


def _squash(text: str) -> str:
    return re.sub(r" +", " ", text)


def _render(*peripherals: Peripheral) -> str:
    device = Device(name="Chip", header_prefix="DC_", peripherals=list(peripherals))
    expand_dim(device)
    resolve_derived(device)
    resolve_defaults(device)
    return CWriter().render(device)


def _dma(*clusters: Cluster) -> Peripheral:
    return Peripheral(
        "DMA",
        0x40020000,
        description="Direct memory access",
        registers=[Register("CFG", 0x0, size=32)],
        clusters=list(clusters),
    )


def test_cluster_becomes_a_nested_type_and_member():
    cluster = Cluster(
        "STAT",
        0x10,
        description="Status block",
        registers=[
            Register("FLAGS", 0x0, size=32),
            Register("ERR", 0x4, size=32, access=Access.READ_ONLY),
        ],
    )
    output = _render(_dma(cluster))
    squashed = _squash(output)
    assert output.index("} dc_dma_stat_t;") < output.index("} dc_dma_t;")  # defined before use
    assert "/* DMA.STAT -- Status block */" in output
    assert "volatile const uint32_t ERR;" in squashed
    assert (
        "REGFORGE_STATIC_ASSERT(offsetof(dc_dma_stat_t, ERR) == DC_DMA_STAT_ERR_OFFSET, "
        'DC_DMA_STAT_ERR_OFFSET_CHECK, "DMA.STAT.ERR offset");' in output
    )
    assert "dc_dma_stat_t STAT;" in squashed
    assert (
        "REGFORGE_STATIC_ASSERT(offsetof(dc_dma_t, STAT) == DC_DMA_STAT_OFFSET, "
        'DC_DMA_STAT_OFFSET_CHECK, "DMA.STAT offset");' in output
    )
    assert "#define DC_DMA_STAT_SIZE (0x00000008UL)" in squashed  # its extent: FLAGS + ERR
    assert (  # a single cluster is checked on its own terms, not via the parent's padding
        "REGFORGE_STATIC_ASSERT(sizeof(dc_dma_stat_t) == DC_DMA_STAT_SIZE, "
        'DC_DMA_STAT_SIZE_CHECK, "DMA.STAT size vs its last register");' in output
    )
    assert "/* DMA.STAT.ERR */" in output
    assert "#define DC_DMA_STAT_ERR (DC_DMA->STAT.ERR)" in output  # the path, not an address


def test_array_cluster_is_padded_asserted_and_indexed():
    cluster = Cluster(
        "CH[%s]",
        0x10,
        dim=Dim(4, 0x10),
        description="DMA channel",
        registers=[
            Register("CTRL", 0x0, size=32, fields=[Field("EN", 0, 1)]),
            Register("SRC", 0x4, size=32),
        ],
    )
    output = _render(_dma(cluster))
    squashed = _squash(output)
    assert "/* DMA.CH -- DMA channel (4 elements, 0x10 bytes apart) */" in output
    assert "uint8_t RESERVED0[DC_DMA_CH_RESERVED0_SIZE];" in squashed  # padded to the stride
    assert "#define DC_DMA_CH_RESERVED0_SIZE (0x00000008UL)" in squashed  # named in the type
    assert (
        "REGFORGE_STATIC_ASSERT(sizeof(dc_dma_ch_t) == DC_DMA_CH_STRIDE, DC_DMA_CH_SIZE_CHECK, "
        '"DMA.CH element size vs dimIncrement");' in output
    )
    assert "dc_dma_ch_t CH[DC_DMA_CH_COUNT];" in squashed
    assert (
        "REGFORGE_STATIC_ASSERT(sizeof(((dc_dma_t *)0)->CH) == "
        'DC_DMA_CH_COUNT * DC_DMA_CH_STRIDE, DC_DMA_CH_ARRAY_CHECK, "DMA.CH array size");' in output
    )
    assert "/* DMA.CH[4].CTRL */" in output
    assert "#define DC_DMA_CH_CTRL(ch_index) (DC_DMA->CH[(ch_index)].CTRL)" in output
    assert "#define DC_DMA_CH_SRC(ch_index) (DC_DMA->CH[(ch_index)].SRC)" in output
    assert (  # the last element is placed outright, so CH[k] is stated, not inferred
        "REGFORGE_STATIC_ASSERT(offsetof(dc_dma_t, CH) + (DC_DMA_CH_COUNT - 1U) * "
        "sizeof(((dc_dma_t *)0)->CH[0]) == DC_DMA_CH_OFFSET + (DC_DMA_CH_COUNT - 1U) * "
        'DC_DMA_CH_STRIDE, DC_DMA_CH_LAST_CHECK, "DMA.CH[3] offset via the struct");' in output
    )
    assert "#define DC_DMA_CH_CTRL_EN_Pos (0U)" in output  # fields are index-free


def test_array_register_inside_array_cluster_takes_two_indices():
    cluster = Cluster(
        "CH[%s]",
        0x10,
        dim=Dim(2, 0x20),
        registers=[Register("BUF[%s]", 0x0, size=32, dim=Dim(4, 4))],
    )
    output = _render(_dma(cluster))
    assert "#define DC_DMA_CH_BUF_COUNT (4U)" in _squash(output)
    assert (  # one parameter per array on the path, outermost first, each named for its array
        "#define DC_DMA_CH_BUF(ch_index, buf_index) "
        "(DC_DMA->CH[(ch_index)].BUF[(buf_index)])" in output
    )
    assert (  # the inner array is placed inside its own type
        "REGFORGE_STATIC_ASSERT(offsetof(dc_dma_ch_t, BUF) + (DC_DMA_CH_BUF_COUNT - 1U) * "
        "sizeof(((dc_dma_ch_t *)0)->BUF[0]) == DC_DMA_CH_BUF_OFFSET + "
        "(DC_DMA_CH_BUF_COUNT - 1U) * DC_DMA_CH_BUF_STRIDE, "
        'DC_DMA_CH_BUF_LAST_CHECK, "DMA.CH.BUF[3] offset via the struct");' in output
    )


def test_copies_of_a_cluster_share_one_type():
    cluster = Cluster("CH%s", 0x10, dim=Dim(3, 0x10), registers=[Register("CTRL", 0x0, size=32)])
    output = _render(_dma(cluster))
    squashed = _squash(output)
    assert output.count("} dc_dma_ch_t;") == 1
    assert all(f"dc_dma_ch_t CH{index};" in squashed for index in range(3))
    assert "#define DC_DMA_CH1_CTRL (DC_DMA->CH1.CTRL)" in output


def test_nested_cluster_types_are_defined_innermost_first():
    inner = Cluster("SUB", 0x8, registers=[Register("R", 0x0, size=32)])
    cluster = Cluster("CH", 0x10, registers=[Register("CTRL", 0x0, size=32)], clusters=[inner])
    output = _render(_dma(cluster))
    assert (
        output.index("} dc_dma_ch_sub_t;")
        < output.index("} dc_dma_ch_t;")
        < output.index("} dc_dma_t;")
    )
    assert "dc_dma_ch_sub_t SUB;" in _squash(output)
    assert "#define DC_DMA_CH_SUB_R (DC_DMA->CH.SUB.R)" in output


def test_header_struct_name_names_the_cluster_type():
    cluster = Cluster(
        "CH", 0x10, header_struct_name="CHANNEL", registers=[Register("CTRL", 0x0, size=32)]
    )
    output = _render(_dma(cluster))
    assert "} dc_dma_channel_t;" in output
    assert "dc_dma_channel_t CH;" in _squash(output)  # the member keeps the cluster's name


def test_same_type_name_wanted_twice_falls_back_to_the_cluster_name():
    first = Cluster("A", 0x10, header_struct_name="CH", registers=[Register("R", 0x0, size=32)])
    second = Cluster(
        "B",
        0x20,
        header_struct_name="CH",
        registers=[Register("R", 0x0, size=32), Register("S", 0x4, size=32)],
    )
    output = _render(_dma(first, second))
    assert "} dc_dma_ch_t;" in output and "} dc_dma_b_t;" in output


def test_family_instances_share_the_cluster_types():
    def channels() -> Cluster:
        return Cluster("CH[%s]", 0x10, dim=Dim(2, 0x10), registers=[Register("CTRL", 0x0, size=32)])

    output = _render(
        Peripheral("DMA0", 0x0, group_name="DMA", clusters=[channels()]),
        Peripheral("DMA1", 0x1000, group_name="DMA", clusters=[channels()]),
    )
    assert output.count("} dc_dma_ch_t;") == 1  # one nested type for the whole family
    assert "#define DC_DMA0_CH_CTRL(ch_index)" in output
    assert "#define DC_DMA1_CH_CTRL(ch_index)" in output


def test_empty_cluster_is_refused():
    with pytest.raises(EmitError, match="no registers"):
        _render(_dma(Cluster("CH", 0x10)))


def test_index_names_repeat_with_a_suffix_when_arrays_share_a_name():
    cluster = Cluster(
        "CH[%s]",
        0x10,
        dim=Dim(2, 0x20),
        registers=[Register("CH[%s]", 0x0, size=32, dim=Dim(4, 4))],
    )
    output = _render(_dma(cluster))
    assert (
        "#define DC_DMA_CH_CH(ch_index, ch2_index) (DC_DMA->CH[(ch_index)].CH[(ch2_index)])"
        in output
    )


def test_unpacked_register_inside_a_cluster_array_falls_back_to_the_address():
    cluster = Cluster(
        "CH[%s]",
        0x10,
        dim=Dim(2, 0x20),
        registers=[Register("D[%s]", 0x0, size=32, dim=Dim(2, 8))],  # stride 8 > 4: holes
    )
    output = _render(_dma(cluster))
    squashed = _squash(output)
    assert "volatile uint32_t D0;" in squashed and "volatile uint32_t D1;" in squashed
    assert (  # no D[] member to index, so the macro is the address sum, both indices named
        "#define DC_DMA_CH_D(ch_index, d_index) (*(volatile uint32_t *)(DC_DMA_BASE + "
        "DC_DMA_CH_OFFSET + (ch_index) * DC_DMA_CH_STRIDE + DC_DMA_CH_D_OFFSET + "
        "(d_index) * DC_DMA_CH_D_STRIDE))" in output
    )


def test_single_cluster_ending_mid_word_is_sized_to_its_alignment():
    # CTRL is 4 bytes, FLAG one byte at 0x4: the extent is 5 but the C type is 8.
    cluster = Cluster(
        "STAT",
        0x10,
        registers=[Register("CTRL", 0x0, size=32), Register("FLAG", 0x4, size=8)],
    )
    output = _render(_dma(cluster))
    assert "#define DC_DMA_STAT_SIZE (0x00000008UL)" in _squash(output)

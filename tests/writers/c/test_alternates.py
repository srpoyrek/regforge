"""C writer: an alternateRegister set is one named union, asserted, with a macro per view."""

import re

from regforge.ir import Access, Cluster, Device, Dim, Peripheral, Register
from regforge.resolve import expand_dim, resolve_alternates, resolve_defaults
from regforge.writers.c import CWriter


def _squash(text: str) -> str:
    return re.sub(r" +", " ", text)


def _render(*registers: Register, clusters: list[Cluster] | None = None) -> str:
    device = Device(
        name="Chip",
        header_prefix="DC_",
        peripherals=[
            Peripheral("TIM", 0x40000000, registers=list(registers), clusters=list(clusters or []))
        ],
    )
    expand_dim(device)
    resolve_alternates(device)
    resolve_defaults(device)
    return CWriter().render(device)


def test_pair_becomes_a_named_union_with_constants_asserts_and_a_macro_per_view():
    output = _render(
        Register("CR1", 0x0, size=32),
        Register("CCMR1_Output", 0x18, size=32, description="Capture/compare mode (output)"),
        Register(
            "CCMR1_Input",
            0x18,
            size=32,
            description="Capture/compare mode (input)",
            alternate_register="CCMR1_Output",
        ),
    )
    squashed = _squash(output)
    assert "#define DC_TIM_CCMR1_OFFSET (0x00000018UL)" in squashed
    assert "#define DC_TIM_CCMR1_SIZE (0x00000004UL)" in squashed
    assert "#define DC_TIM_CCMR1_OUTPUT_OFFSET" not in output  # views have no constants
    assert (
        "    union {\n"
        "        volatile uint32_t Output;  /* 0x18  Capture/compare mode (output) */\n"
        "        volatile uint32_t Input;   /* 0x18  Capture/compare mode (input) */\n"
        "    } CCMR1;  /* 0x18  one register, 2 views */\n"
    ) in output
    assert (
        "REGFORGE_STATIC_ASSERT(offsetof(dc_tim_t, CCMR1) == DC_TIM_CCMR1_OFFSET, "
        'DC_TIM_CCMR1_OFFSET_CHECK, "TIM.CCMR1 offset");' in output
    )
    assert (
        "REGFORGE_STATIC_ASSERT(sizeof(((dc_tim_t *)0)->CCMR1) == DC_TIM_CCMR1_SIZE, "
        'DC_TIM_CCMR1_SIZE_CHECK, "TIM.CCMR1 union size");' in output
    )
    # A view's own offset is not asserted: every union member is at offset zero, so
    # the union's asserted offset already covers it.
    assert "CCMR1.Input) ==" not in output
    assert "CCMR1_INPUT_OFFSET_CHECK" not in output
    assert (
        "/* TIM.CCMR1_Output - Capture/compare mode (output)  [alternate: CCMR1_Input] */\n"
        "#define DC_TIM_CCMR1_OUTPUT (DC_TIM->CCMR1.Output)\n"
    ) in output
    assert "#define DC_TIM_CCMR1_INPUT (DC_TIM->CCMR1.Input)" in output


def test_views_keep_their_own_qualifiers_and_types():
    output = _render(
        Register("DR", 0x4, size=32),
        Register("RXD", 0x4, size=32, access=Access.READ_ONLY, alternate_register="DR"),
        Register("DR8", 0x4, size=8, alternate_register="DR"),
    )
    squashed = _squash(output)
    assert "volatile uint32_t DR;" in squashed
    assert "volatile const uint32_t RXD;" in squashed  # read-only view: const
    assert "volatile uint8_t DR8;" in squashed  # narrow view: narrow type
    assert "} DR; /* 0x04 one register, 3 views */" in squashed  # rule 2: named after DR
    assert "#define DC_TIM_DR_SIZE (0x00000004UL)" in squashed  # the widest view
    assert "#define DC_TIM_RXD (DC_TIM->DR.RXD)" in output
    assert "/* TIM.DR  [alternate: RXD, DR8] */" in output


def test_union_array_is_indexed_like_a_register_array():
    output = _render(
        Register("CC[%s]", 0x10, size=32, dim=Dim(4, 4)),
        Register("CCI[%s]", 0x10, size=32, dim=Dim(4, 4), alternate_register="CC[%s]"),
    )
    squashed = _squash(output)
    assert "} CC[DC_TIM_CC_COUNT]; /* 0x10 one register, 2 views */" in squashed
    assert "#define DC_TIM_CC_STRIDE (0x00000004UL)" in squashed
    assert "#define DC_TIM_CC(cc_index) (DC_TIM->CC[(cc_index)].CC)" in output
    assert "#define DC_TIM_CCI(cc_index) (DC_TIM->CC[(cc_index)].CCI)" in output
    assert (  # asserted like any array: offset, then one element against the stride
        "REGFORGE_STATIC_ASSERT(sizeof(((dc_tim_t *)0)->CC[0]) == DC_TIM_CC_STRIDE, "
        'DC_TIM_CC_STRIDE_CHECK, "TIM.CC element size vs dimIncrement");' in output
    )
    assert "DC_TIM_CC_ARRAY_CHECK" not in output
    assert "DC_TIM_CC_LAST_CHECK" not in output


def test_unpacked_union_array_is_flat_unions_with_an_address_macro():
    output = _render(
        Register("CC[%s]", 0x10, size=32, dim=Dim(2, 8)),
        Register("CCI[%s]", 0x10, size=32, dim=Dim(2, 8), alternate_register="CC[%s]"),
    )
    squashed = _squash(output)
    assert "} CC0; /* 0x10 one register, 2 views */" in squashed
    assert "} CC1; /* 0x18 one register, 2 views */" in squashed
    assert (
        "REGFORGE_STATIC_ASSERT(offsetof(dc_tim_t, CC1) == DC_TIM_CC_OFFSET + 1U * "
        'DC_TIM_CC_STRIDE, DC_TIM_CC1_OFFSET_CHECK, "TIM.CC1 offset");' in output
    )
    # Each element carries its own member offset above; its views carry none,
    # because a union member is always at offset zero.
    assert "CC1.CCI) ==" not in output
    assert (
        "#define DC_TIM_CCI(cc_index) (*(volatile uint32_t *)"
        "(DC_TIM_BASE + DC_TIM_CC_OFFSET + (cc_index) * DC_TIM_CC_STRIDE))" in output
    )


def test_union_inside_a_cluster_array_is_reached_through_both():
    cluster = Cluster(
        "CH[%s]",
        0x10,
        dim=Dim(2, 0x8),
        registers=[
            Register("CTRL", 0x0, size=32),
            Register("XFER_Mem", 0x4, size=32),
            Register("XFER_Periph", 0x4, size=32, alternate_register="XFER_Mem"),
        ],
    )
    output = _render(Register("CFG", 0x0, size=32), clusters=[cluster])
    squashed = _squash(output)
    assert "#define DC_TIM_CH_XFER_SIZE (0x00000004UL)" in squashed
    assert "} XFER; /* 0x04 one register, 2 views */" in squashed
    assert (  # the union is asserted inside the cluster's own type
        "REGFORGE_STATIC_ASSERT(sizeof(((dc_tim_ch_t *)0)->XFER) == DC_TIM_CH_XFER_SIZE, "
        'DC_TIM_CH_XFER_SIZE_CHECK, "TIM.CH.XFER union size");' in output
    )
    assert "XFER.Periph) ==" not in output  # a view needs no offset assert
    assert "#define DC_TIM_CH_XFER_MEM(ch_index) (DC_TIM->CH[(ch_index)].XFER.Mem)" in output


def test_unrelated_registers_at_one_offset_are_refused_with_the_hint():
    import pytest

    from regforge.writers.base import EmitError

    with pytest.raises(EmitError, match=r"overlaps the preceding member \(add <alternateRegister>"):
        _render(Register("A", 0x0, size=32), Register("B", 0x0, size=32))

"""The canonical fixture (minimal.svd) exercises Layer 1 features end-to-end.

test_golden diffs the whole output byte-for-byte; these name the specific
features the enriched fixture is there to demonstrate, so a regression points
at the feature rather than "the golden changed".
"""

from regforge.writers.c import CWriter


def test_fixture_honors_header_prefix(demo_device):
    assert demo_device.header_prefix == "DC_"
    output = CWriter().render(demo_device)
    assert "#define DC_GPIOA_BASE" in output  # hardware identifiers prefixed
    assert "#define DEMOMCU_BUS_WIDTH" in output  # metadata not double-prefixed


def test_fixture_emits_reset_mask_only_where_partial(demo_device):
    output = CWriter().render(demo_device)
    assert "#define DC_GPIOA_ODR_RESET_MASK (0x0000FFFFUL)" in output  # ODR: partial
    assert "DC_GPIOA_MODER_RESET_MASK" not in output  # MODER: no mask -> suppressed


def test_fixture_preserves_vendor_extensions_without_emitting(demo_device):
    assert demo_device.vendor_extensions_xml is not None
    assert "calibrated" in demo_device.vendor_extensions_xml
    assert "calibrated" not in CWriter().render(demo_device)  # opaque, never emitted

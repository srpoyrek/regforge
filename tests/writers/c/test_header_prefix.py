"""C writer: honor headerDefinitionsPrefix; keep vendorExtensions opaque."""

from regforge.ir import Device, Field, Peripheral, Register
from regforge.writers.c import CWriter


def _render(prefix, *, vendor_extensions_xml=None):
    device = Device(
        name="Chip",
        header_prefix=prefix,
        vendor_extensions_xml=vendor_extensions_xml,
        peripherals=[
            Peripheral(
                name="GPIO",
                base_address=0x1000,
                registers=[
                    Register(
                        name="CR",
                        address_offset=0,
                        size=32,
                        fields=[Field("EN", bit_offset=0, bit_width=1)],
                    )
                ],
            )
        ],
    )
    return CWriter().render(device)


def test_prefix_applied_to_hardware_identifiers():
    output = _render("NRF_")
    assert "#define NRF_GPIO_BASE" in output  # peripheral
    assert "#define NRF_GPIO_CR " in output  # register accessor
    assert "#define NRF_GPIO_CR_EN_Pos" in output  # field-level, too
    assert "#define NRF_GPIO_CR_EN_Msk" in output
    # Device-name-based metadata is NOT re-prefixed (no double namespacing).
    assert "#define CHIP_BUS_WIDTH" in output
    assert "NRF_CHIP_BUS_WIDTH" not in output


def test_no_prefix_by_default():
    output = _render(None)
    assert "#define GPIO_BASE" in output
    assert "#define GPIO_CR_EN_Pos" in output
    assert "NRF_" not in output


def test_vendor_extensions_are_not_emitted():
    # Preserved in the IR, but opaque: never interpreted, never leaked to output.
    output = _render(None, vendor_extensions_xml="<esp:secret>hidden</esp:secret>")
    assert "hidden" not in output
    assert "secret" not in output

"""Device: the root of the register map."""

from regforge.ir import DEFAULT_ADDRESS_UNIT_BITS, DEFAULT_BUS_WIDTH, Device, Peripheral


def test_a_device_with_only_a_name_has_the_schemas_defaults():
    device = Device("D")
    assert (device.address_unit_bits, device.bus_width) == (8, 32)
    assert device.peripherals == [] and device.cpu is None


def test_the_schema_defaults_are_named():
    assert (DEFAULT_ADDRESS_UNIT_BITS, DEFAULT_BUS_WIDTH) == (8, 32)


def test_the_identity_and_the_register_defaults_are_absent_until_stated():
    device = Device("D")
    for name in (
        "description",
        "vendor",
        "series",
        "version",
        "license_text",
        "header_prefix",
        "vendor_extensions_xml",
        "default_size",
        "default_access",
        "default_reset_value",
        "default_reset_mask",
        "default_protection",
    ):
        assert getattr(device, name) is None, name


def test_each_device_has_a_list_of_peripherals_of_its_own():
    one, other = Device("A"), Device("B")
    one.peripherals.append(Peripheral("P", 0x0))
    assert other.peripherals == []


def test_two_devices_are_equal_when_what_they_state_is():
    assert Device("D", vendor="V") == Device("D", vendor="V")
    assert Device("D", vendor="V") != Device("D", vendor="W")

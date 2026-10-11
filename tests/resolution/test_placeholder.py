"""is_placeholder_name: the Reserved a vendor gives to everything it leaves unused."""

import inspect

import pytest

import regforge.resolution.placeholder as placeholder_module
from regforge.resolution import is_placeholder_name


@pytest.mark.parametrize(
    "name",
    ["Reserved", "reserved", "RESERVED", "RESERVED_", "Reserved1", "RESERVED_0", "reserved_12"],
)
def test_reserved_in_any_case_with_an_optional_underscore_or_digits_is_a_placeholder(name):
    assert is_placeholder_name(name)


@pytest.mark.parametrize(
    "name", ["", "RES", "Reserve", "Reserved_BITS", "XRESERVED", "RESERVED X", "ENABLED", "RSVD"]
)
def test_any_other_name_is_a_real_one(name):
    assert not is_placeholder_name(name)


def test_the_whole_name_must_match():
    assert not is_placeholder_name("Reserved7x")
    assert not is_placeholder_name("MyReserved")


# --- layering ----------------------------------------------------------------------


def test_the_placeholder_module_knows_nothing_of_the_register_map():
    source = inspect.getsource(placeholder_module)
    assert "regforge" not in source
    for element in ("Field", "EnumSet", "EnumeratedValue", "Register", "Peripheral", "Device"):
        assert element not in source

"""DataTypeHtml: the C type a register is meant to be read as, written as the schema spells it."""

import pytest

from regforge.ir import DataType
from regforge.writers.html.device.peripheral.register.data_type import DataTypeHtml


@pytest.mark.parametrize("data_type", list(DataType))
def test_every_type_reads_as_the_schemas_spelling(data_type):
    assert DataTypeHtml().label(data_type) == data_type.value


def test_a_pointer_type_keeps_its_star():
    assert DataTypeHtml().label(DataType.UINT8_PTR) == "uint8_t *"


def test_a_register_that_states_no_type_has_no_label():
    assert DataTypeHtml().label(None) is None

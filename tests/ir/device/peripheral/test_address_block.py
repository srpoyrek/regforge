"""AddressBlock: a peripheral's declared memory footprint."""

import pytest

from regforge.ir import BLOCK_BUFFER, BLOCK_REGISTERS, BLOCK_RESERVED, AddressBlock, Protection


def test_the_usages_are_the_schemas_words():
    assert (BLOCK_REGISTERS, BLOCK_BUFFER, BLOCK_RESERVED) == ("registers", "buffer", "reserved")


def test_a_block_keeps_its_offset_and_size():
    block = AddressBlock(0x10, 0x20)
    assert (block.offset, block.size) == (0x10, 0x20)
    assert block.usage is None and block.protection is None


@pytest.mark.parametrize(
    ("usage", "holds"),
    [(None, True), (BLOCK_REGISTERS, True), (BLOCK_BUFFER, False), (BLOCK_RESERVED, False)],
)
def test_only_a_block_of_registers_holds_registers(usage, holds):
    assert AddressBlock(0x0, 0x4, usage).holds_registers is holds


def test_only_a_buffer_block_is_a_buffer():
    assert AddressBlock(0x0, 0x4, BLOCK_BUFFER).is_buffer
    for usage in (None, BLOCK_REGISTERS, BLOCK_RESERVED):
        assert not AddressBlock(0x0, 0x4, usage).is_buffer


def test_a_block_can_say_what_access_to_it_needs():
    assert AddressBlock(0x0, 0x4, protection=Protection.SECURE).protection is Protection.SECURE

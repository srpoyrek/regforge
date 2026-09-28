"""C writer: peripheral name + base address as a distinct type + typed instance.

Each peripheral becomes its own C struct type with a typed handle at its base,
so passing the wrong peripheral to a function is a compile error -- and the
handle is a real symbol, not a cast-macro like CMSIS emits.
"""

import re

import pytest

from regforge.ir import Access, Device, Peripheral, Register
from regforge.resolve import resolve_defaults, resolve_derived
from regforge.writers.base import EmitError
from regforge.writers.c import CWriter


def _squash(text: str) -> str:
    """Collapse runs of spaces so assertions ignore column-alignment padding."""
    return re.sub(r" +", " ", text)


def test_emits_struct_type_and_typed_instance(demo_device):
    output = CWriter().render(demo_device)
    squashed = _squash(output)
    # A distinct struct type per peripheral; the _t name is fully lower-case.
    assert "} dc_gpioa_t;" in output
    assert "volatile uint32_t MODER;" in squashed
    assert "volatile uint32_t ODR;" in squashed
    # Reserved padding fills 0x04..0x10 (IDR sits at 0x10) so offsets stay true.
    assert "uint8_t RESERVED0[12];" in squashed
    # The instance is a typed, non-redefinable symbol -- not a cast-macro.
    assert (
        "REGFORGE_MAYBE_UNUSED static dc_gpioa_t *const DC_GPIOA = (dc_gpioa_t *)DC_GPIOA_BASE;"
        in output
    )
    # The base-address define is kept for constant-expression contexts.
    assert "#define DC_GPIOA_BASE" in output


def test_offset_static_asserts_prove_layout(demo_device):
    output = CWriter().render(demo_device)
    # Each register carries a compile-time proof it sits at its declared offset;
    # the compile matrix then makes a real compiler check them.
    assert "offsetof(dc_gpioa_t, MODER) == DC_GPIOA_MODER_OFFSET" in output
    assert "offsetof(dc_gpioa_t, IDR) == DC_GPIOA_IDR_OFFSET" in output
    assert "offsetof(dc_gpioa_t, ODR) == DC_GPIOA_ODR_OFFSET" in output
    # No assert on the reserved gap -- a register's offset proves the pad before it.
    assert "offsetof(dc_gpioa_t, RESERVED0)" not in output


def test_derived_family_emits_one_type_and_two_instances():
    device = Device(
        name="Chip",
        peripherals=[
            Peripheral(
                name="UART0",
                base_address=0x4000,
                registers=[Register("DR", 0x0, size=32, access=Access.READ_WRITE)],
            ),
            Peripheral(name="UART1", base_address=0x5000, derived_from="UART0"),
        ],
    )
    resolve_defaults(device)
    resolve_derived(device)
    output = CWriter().render(device)
    # ONE shared type; both instances are of it -> one driver works for both.
    assert output.count("} uart0_t;") == 1
    assert "static uart0_t *const UART0 " in output
    assert "static uart0_t *const UART1 " in output
    # offsetof asserts emitted once per type, not per instance.
    assert output.count("offsetof(uart0_t, DR)") == 1
    # per-instance register macros, each at its own base.
    assert "#define UART0_DR (" in output
    assert "#define UART1_DR (" in output


def test_distinct_type_per_peripheral():
    device = Device(
        name="Chip",
        peripherals=[
            Peripheral(
                name="GPIOA",
                base_address=0x4000,
                registers=[Register(name="MODER", address_offset=0, size=32)],
            ),
            Peripheral(
                name="TIM1",
                base_address=0x5000,
                registers=[Register(name="CR1", address_offset=0, size=32)],
            ),
        ],
    )
    output = CWriter().render(device)
    # Two peripherals -> two distinct C types, so mixing them cannot compile.
    assert "} gpioa_t;" in output
    assert "} tim1_t;" in output
    assert "static gpioa_t *const GPIOA " in output
    assert "static tim1_t *const TIM1 " in output


def test_overlapping_registers_are_refused():
    device = Device(
        name="Chip",
        peripherals=[
            Peripheral(
                name="P",
                base_address=0x0,
                registers=[
                    Register(name="A", address_offset=0x0, size=32),  # 0x0..0x4
                    Register(name="B", address_offset=0x2, size=32),  # overlaps A
                ],
            )
        ],
    )
    with pytest.raises(EmitError) as exc:
        CWriter().render(device)
    assert "overlaps" in str(exc.value)


def test_member_type_comes_from_resolved_size():
    # A register with no <size> of its own inherits it (device default here) and
    # still gets a correct struct member type.
    device = Device(
        name="Chip",
        default_size=16,
        peripherals=[
            Peripheral(
                name="P",
                base_address=0x0,
                registers=[Register(name="R", address_offset=0x0)],
            ),
        ],
    )
    resolve_defaults(device)
    assert device.peripherals[0].registers[0].size == 16  # inherited, not None
    assert "volatile uint16_t R;" in _squash(CWriter().render(device))


def test_read_only_member_and_macro_are_const():
    device = Device(
        name="Chip",
        peripherals=[
            Peripheral(
                name="P",
                base_address=0x0,
                registers=[
                    Register(name="RW", address_offset=0x0, size=32, access=Access.READ_WRITE),
                    Register(name="RO", address_offset=0x4, size=32, access=Access.READ_ONLY),
                ],
            ),
        ],
    )
    output = CWriter().render(device)
    squashed = _squash(output)
    assert "volatile uint32_t RW;" in squashed  # read-write: writable
    assert "volatile const uint32_t RO;" in squashed  # read-only: const struct member
    # The flat macro is const too, so it cannot be a write backdoor to a RO register.
    assert "#define P_RO (*(volatile const uint32_t *)" in output
    assert "#define P_RW (*(volatile uint32_t *)" in output


def test_size_less_register_is_refused_without_resolution():
    # Without resolve_defaults, size stays None -- the emitter refuses it rather
    # than guessing. The resolution pass is what makes the struct member typeable.
    device = Device(
        name="Chip",
        peripherals=[
            Peripheral(
                name="P",
                base_address=0x0,
                registers=[Register(name="R", address_offset=0x0)],
            ),
        ],
    )
    with pytest.raises(EmitError):
        CWriter().render(device)


def test_render_is_deterministic():
    # Same IR -> byte-identical output. The internal id()-keyed layout lookup
    # must not leak memory addresses (or any nondeterminism) into the header.
    device = Device(
        name="Chip",
        peripherals=[
            Peripheral(name="A", base_address=0x0, registers=[Register("R", 0x0, size=32)]),
            Peripheral(name="B", base_address=0x1000, registers=[Register("R", 0x0, size=32)]),
        ],
    )
    assert CWriter().render(device) == CWriter().render(device)


def test_macro_rule_base_kept_identity_is_the_type(demo_device):
    # Base address is a consumed value -> macro; peripheral identity is
    # enforced by the C type -> no macro (a _KIND macro would be dead weight).
    output = CWriter().render(demo_device)
    assert "#define DC_GPIOA_BASE" in output  # consumed value -> macro
    assert "dc_gpioa_t *const DC_GPIOA" in output  # identity is the type + instance
    assert "DC_GPIOA_KIND" not in output
    assert "DC_GPIOA_TYPE" not in output

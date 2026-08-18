"""C writer: CPU constants, endian assert, FPU guard, priority helper.

Every emission is conditional on the field being present: unknown or omitted
values must produce nothing, never a guess that could break valid user code.
"""

from regforge.ir import Cpu, Device
from regforge.writers.c import CWriter


def _render(**cpu_kwargs):
    return CWriter().render(Device(name="Chip", cpu=Cpu(**cpu_kwargs)))


def test_cpu_constants_emitted():
    output = _render(
        name="CM4",
        revision="r0p1",
        nvic_prio_bits=3,
        num_interrupts=48,
        fpu_present=True,
        mpu_present=True,
        vtor_present=True,
    )
    assert '#define CHIP_CPU_CORE "CM4"' in output
    assert '#define CHIP_CPU_REVISION "r0p1"' in output
    assert "#define CHIP_NVIC_PRIO_BITS 3" in output
    assert "#define CHIP_NUM_IRQS 48" in output
    assert "#define CHIP_HAS_FPU 1" in output
    assert "#define CHIP_HAS_MPU 1" in output
    assert "#define CHIP_HAS_VTOR 1" in output


def test_absent_fields_emit_nothing():
    output = _render(name="CM0")
    assert "CHIP_CPU_CORE" in output
    assert "CHIP_HAS_FPU" not in output  # fpu_present is None -> not emitted
    assert "CHIP_NVIC_PRIO_BITS" not in output


def test_no_cpu_block_emits_no_cpu_section():
    output = CWriter().render(Device(name="Chip"))
    assert "CPU_CORE" not in output
    assert "irq_prio" not in output
    assert "#include <assert.h>" not in output


def test_priority_helper_is_msb_aligned():
    output = _render(nvic_prio_bits=2)
    assert "#define CHIP_IRQ_PRIO_LEVELS (1U << CHIP_NVIC_PRIO_BITS)" in output
    assert "uint8_t chip_irq_prio(uint8_t priority)" in output
    assert "priority << (8U - CHIP_NVIC_PRIO_BITS)" in output
    assert "assert(priority < CHIP_IRQ_PRIO_LEVELS)" in output
    assert "#include <assert.h>" in output


def test_priority_helper_omitted_without_prio_bits():
    output = _render(name="CM0")
    assert "irq_prio" not in output


def test_fpu_guard_only_when_fpu_absent():
    assert "__ARM_FP" in _render(fpu_present=False)
    assert "has no FPU" in _render(fpu_present=False)
    assert "__ARM_FP" not in _render(fpu_present=True)  # present -> no guard
    assert "__ARM_FP" not in _render(name="CM0")  # unknown -> no guard


def test_endian_assert():
    assert "__ORDER_LITTLE_ENDIAN__" in _render(endian="little")
    assert "__ORDER_BIG_ENDIAN__" in _render(endian="big")
    assert "__BYTE_ORDER__" not in _render(name="CM0")  # unknown -> no assert

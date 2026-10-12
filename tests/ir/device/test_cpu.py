"""Cpu: the processor core a device is built around; every fact about it is optional."""

from dataclasses import fields

from regforge.ir import Cpu


def test_a_cpu_states_nothing_until_it_is_told_to():
    cpu = Cpu()
    assert all(getattr(cpu, f.name) is None for f in fields(cpu))


def test_a_cpu_keeps_what_the_file_states():
    cpu = Cpu(name="CM4", revision="r0p1", endian="little", fpu_present=True, nvic_prio_bits=3)
    assert (cpu.name, cpu.revision, cpu.endian) == ("CM4", "r0p1", "little")
    assert cpu.fpu_present is True and cpu.nvic_prio_bits == 3
    assert cpu.mpu_present is None  # left out stays unknown, never guessed


def test_a_flag_that_is_false_is_not_the_same_as_one_that_is_absent():
    assert Cpu(mpu_present=False).mpu_present is False
    assert Cpu().mpu_present is None

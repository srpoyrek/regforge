"""Interrupt: a line a peripheral raises, named for the vector it uses."""

from regforge.ir import Interrupt


def test_an_interrupt_has_a_name_and_a_vector():
    interrupt = Interrupt("UART0", 5)
    assert (interrupt.name, interrupt.value) == ("UART0", 5)
    assert interrupt.description is None


def test_an_interrupt_keeps_its_description():
    assert Interrupt("TIM1", 25, "Timer 1 overflow").description == "Timer 1 overflow"


def test_two_interrupts_with_one_vector_are_still_two():
    assert Interrupt("A", 3) != Interrupt("B", 3)
    assert Interrupt("A", 3).value == Interrupt("B", 3).value

"""Device interrupt topology: device-wide collection, dedup, ordering, sharing."""

from regforge.interrupts import all_interrupts, shared_vectors
from regforge.ir import Device, Interrupt, Peripheral


def _device(*peripherals: Peripheral) -> Device:
    return Device(name="Chip", peripherals=list(peripherals))


def test_collects_across_peripherals_sorted_by_value():
    device = _device(
        Peripheral(name="UART0", base_address=0x0, interrupts=[Interrupt("UART0", 20)]),
        Peripheral(
            name="DMA",
            base_address=0x1000,
            interrupts=[Interrupt("DMA_CH0", 10), Interrupt("DMA_ERR", 11)],
        ),
    )
    assert [(i.name, i.value) for i in all_interrupts(device)] == [
        ("DMA_CH0", 10),
        ("DMA_ERR", 11),
        ("UART0", 20),
    ]


def test_shared_vector_deduplicated_by_name():
    # One vector referenced by two peripherals appears a single time.
    device = _device(
        Peripheral(name="TIM1", base_address=0x0, interrupts=[Interrupt("TIM1_BRK_TIM9", 24)]),
        Peripheral(name="TIM9", base_address=0x400, interrupts=[Interrupt("TIM1_BRK_TIM9", 24)]),
    )
    result = all_interrupts(device)
    assert len(result) == 1
    assert result[0].name == "TIM1_BRK_TIM9"


def test_device_without_interrupts_is_empty():
    device = _device(Peripheral(name="GPIOA", base_address=0x0))
    assert all_interrupts(device) == []


def test_shared_vectors_detects_same_value_across_peripherals():
    # SPI0 and SPI1 both raise vector 30 (different interrupt names, same number).
    device = _device(
        Peripheral(name="SPI0", base_address=0x0, interrupts=[Interrupt("SPI0", 30)]),
        Peripheral(name="SPI1", base_address=0x400, interrupts=[Interrupt("SPI1", 30)]),
        Peripheral(name="UART0", base_address=0x800, interrupts=[Interrupt("UART0", 20)]),
    )
    # Keyed on value; UART0 (a singleton vector) is omitted; names in decl order.
    assert shared_vectors(device) == {30: ["SPI0", "SPI1"]}


def test_shared_vectors_catches_same_named_vector_referenced_twice():
    # STM32 style: one named vector referenced by two peripherals.
    device = _device(
        Peripheral(name="TIM1", base_address=0x0, interrupts=[Interrupt("TIM1_BRK_TIM9", 24)]),
        Peripheral(name="TIM9", base_address=0x400, interrupts=[Interrupt("TIM1_BRK_TIM9", 24)]),
    )
    assert shared_vectors(device) == {24: ["TIM1", "TIM9"]}


def test_shared_vectors_empty_when_all_distinct():
    device = _device(
        Peripheral(name="A", base_address=0x0, interrupts=[Interrupt("A", 1)]),
        Peripheral(name="B", base_address=0x400, interrupts=[Interrupt("B", 2)]),
    )
    assert shared_vectors(device) == {}

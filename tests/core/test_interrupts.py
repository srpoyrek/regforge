"""Device interrupt topology: device-wide collection, dedup, ordering."""

from regforge.interrupts import all_interrupts
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

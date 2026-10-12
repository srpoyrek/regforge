"""An interrupt line a peripheral raises."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Interrupt:
    """An interrupt line a peripheral raises (SVD ``<interrupt>``).

    Attributes:
        name: Interrupt identifier, e.g. ``"UART0"`` or ``"TIM1_BRK_TIM9"``.
            Names the ``<name>_IRQn`` enumerator; may differ from the peripheral
            name and may be shared by several peripherals (one vector, many
            sources).
        value: Vector number (NVIC position); the enumerator's value.
        description: Optional human-readable description.
    """

    name: str
    value: int
    description: str | None = None

"""Processor-architecture knowledge shared across output writers.

Which interrupt controller a core integrates -- and where that controller's
registers live -- is a hardware fact, not a property of any target language, so
it lives here where every writer (C, Rust, C++, ...) can consume it instead of
each re-encoding the core list.

Extending:
    * a new core -> one entry in :data:`CORE_CONTROLLERS`;
    * a new controller kind -> one :class:`InterruptController` member, its
      register data (e.g. another ``*_REGISTER_BANKS`` table), and a writer
      emitter that renders that data in its own syntax.
"""

from __future__ import annotations

from enum import Enum

from .ir import Cpu


class InterruptController(Enum):
    """The interrupt controller a CPU core integrates."""

    NVIC = "nvic"  # Arm Cortex-M / SecurCore -- fixed-address, inside the core
    GIC = "gic"  # Arm Cortex-A / Cortex-R
    PLIC = "plic"  # RISC-V platform-level interrupt controller
    CLIC = "clic"  # RISC-V core-local interrupt controller


#: CMSIS-SVD ``<cpu><name>`` token -> the interrupt controller that core
#: integrates. Names are matched upper-cased. An unknown/absent name maps to
#: ``None`` so a writer emits no controller code (safe default). Add a core by
#: adding a line here -- no writer change needed for another NVIC core.
CORE_CONTROLLERS: dict[str, InterruptController] = {
    # Arm Cortex-M and SecurCore: NVIC at the fixed System Control Space
    # address on every vendor's part.
    "CM0": InterruptController.NVIC,
    "CM0PLUS": InterruptController.NVIC,
    "CM1": InterruptController.NVIC,
    "CM3": InterruptController.NVIC,
    "CM4": InterruptController.NVIC,
    "CM7": InterruptController.NVIC,
    "CM23": InterruptController.NVIC,
    "CM33": InterruptController.NVIC,
    "CM35P": InterruptController.NVIC,
    "CM52": InterruptController.NVIC,
    "CM55": InterruptController.NVIC,
    "CM85": InterruptController.NVIC,
    "SC000": InterruptController.NVIC,
    "SC300": InterruptController.NVIC,
    "ARMV8MML": InterruptController.NVIC,
    "ARMV8MBL": InterruptController.NVIC,
    "ARMV81MML": InterruptController.NVIC,
}


#: NVIC register banks (``name``, absolute ``address``, ``purpose``). ARM fixes
#: these in the System Control Space for every Cortex-M core, so the data is
#: shared; each writer renders it in its own syntax.
NVIC_REGISTER_BANKS: tuple[dict, ...] = (
    {"name": "ISER", "address": 0xE000E100, "purpose": "set-enable"},
    {"name": "ICER", "address": 0xE000E180, "purpose": "clear-enable"},
    {"name": "ISPR", "address": 0xE000E200, "purpose": "set-pending"},
    {"name": "ICPR", "address": 0xE000E280, "purpose": "clear-pending"},
    {"name": "IPR", "address": 0xE000E400, "purpose": "priority"},
)


def controller_for(cpu: Cpu | None) -> InterruptController | None:
    """The interrupt controller for ``cpu``, or ``None`` if the core is unknown."""
    if cpu is None or cpu.name is None:
        return None
    return CORE_CONTROLLERS.get(cpu.name.strip().upper())


def is_cortex_m(cpu: Cpu | None) -> bool:
    """Whether ``cpu`` is an Arm Cortex-M core (NVIC-based)."""
    return controller_for(cpu) is InterruptController.NVIC

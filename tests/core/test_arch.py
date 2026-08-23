"""Shared architecture knowledge: core -> interrupt-controller classification."""

from regforge.arch import (
    InterruptController,
    controller_for,
    is_cortex_m,
)
from regforge.ir import Cpu


def test_cortex_m_cores_map_to_nvic():
    for name in ("CM0", "CM0PLUS", "CM4", "CM33", "SC300"):
        assert controller_for(Cpu(name=name)) is InterruptController.NVIC
        assert is_cortex_m(Cpu(name=name))


def test_core_name_is_matched_case_insensitively():
    assert is_cortex_m(Cpu(name="cm0plus"))
    assert is_cortex_m(Cpu(name=" CM4 "))


def test_unknown_or_absent_core_has_no_controller():
    assert controller_for(Cpu(name="RV32IMAC")) is None  # RISC-V: PLIC/CLIC, not in the map yet
    assert controller_for(Cpu(name=None)) is None
    assert controller_for(None) is None
    assert not is_cortex_m(Cpu(name="CA7"))  # Cortex-A uses a GIC, not an NVIC

"""BitResolution: what is wrong with who claims the bits of one register.

It is given plain data, the width and each bit's claimants, and knows nothing above a bit.
"""

import inspect

from regforge.finding import Severity
from regforge.resolution import BitResolution, bit


def _resolution(claims: dict[int, list[str]], width: int = 8) -> BitResolution:
    return BitResolution(width, claims, "P.R")


def _messages(findings):
    return [finding.message for finding in findings]


def test_a_bit_with_two_claimants_is_a_warning():
    resolution = _resolution({0: ["MODE"], 1: ["MODE", "STATE"], 2: ["STATE"]})
    (finding,) = resolution.collisions()
    assert finding.severity is Severity.WARNING
    assert finding.message == "P.R: bit 1 is claimed by MODE and STATE"


def test_a_run_of_shared_bits_is_one_finding():
    claims = {position: ["A", "B"] for position in range(4, 8)}
    assert _messages(_resolution(claims).collisions()) == ["P.R: bits 4..7 are claimed by A and B"]


def test_separate_runs_are_separate_findings():
    claims = {0: ["A", "B"], 6: ["A", "C"], 7: ["A", "C"]}
    assert _messages(_resolution(claims).collisions()) == [
        "P.R: bit 0 is claimed by A and B",
        "P.R: bits 6..7 are claimed by A and C",
    ]


def test_neighbouring_bits_with_different_claimants_are_different_runs():
    claims = {2: ["A", "B"], 3: ["A", "C"]}
    assert _messages(_resolution(claims).collisions()) == [
        "P.R: bit 2 is claimed by A and B",
        "P.R: bit 3 is claimed by A and C",
    ]


def test_every_claimant_is_named_in_the_order_given():
    assert _messages(_resolution({3: ["A", "B", "C"]}).collisions()) == [
        "P.R: bit 3 is claimed by A and B and C"
    ]


def test_bits_with_one_claimant_or_none_are_silent():
    assert _resolution({0: ["A"], 1: ["A"], 5: ["B"]}).collisions() == []
    assert _resolution({}).collisions() == []


def test_positions_at_or_beyond_the_width_are_not_bits_of_the_register():
    assert _resolution({8: ["A", "B"], 9: ["A", "B"]}, width=8).collisions() == []
    assert _messages(_resolution({7: ["A", "B"], 8: ["A", "B"]}, width=8).collisions()) == [
        "P.R: bit 7 is claimed by A and B"
    ]


def test_the_findings_are_the_collisions():
    resolution = _resolution({1: ["A", "B"]})
    assert resolution.findings() == resolution.collisions()


def test_str_is_the_report_one_finding_per_line():
    resolution = _resolution({0: ["A", "B"], 6: ["A", "C"]})
    assert str(resolution) == (
        "warning: P.R: bit 0 is claimed by A and B\nwarning: P.R: bit 6 is claimed by A and C"
    )


def test_str_is_empty_when_nothing_is_wrong():
    assert str(_resolution({0: ["A"]})) == ""


def test_the_bit_class_imports_nothing_above_a_bit():
    # The layering rule: a bit knows bits. Fields and registers are the collector's business.
    source = inspect.getsource(bit)
    assert "regforge.ir" not in source
    assert "Field" not in source and "Register" not in source

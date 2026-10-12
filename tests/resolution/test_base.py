"""Resolution: what every element's resolution class has in common."""

import pytest

from regforge.finding import Finding, Severity
from regforge.resolution import Resolution


class _Both(Resolution):
    def findings(self) -> list[Finding]:
        return [Finding(Severity.WARNING, "P.R: first"), Finding(Severity.ERROR, "P.R: second")]


class _Neither(Resolution):
    def findings(self) -> list[Finding]:
        return []


def test_the_base_cannot_be_built_without_saying_what_it_finds():
    with pytest.raises(TypeError):
        Resolution()


def test_the_report_is_one_finding_per_line():
    assert str(_Both()) == "warning: P.R: first\nerror: P.R: second"


def test_an_element_with_nothing_wrong_has_an_empty_report():
    assert str(_Neither()) == ""

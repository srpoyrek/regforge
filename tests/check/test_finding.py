"""Finding: one thing a rule found wrong, and how seriously to take it."""

from regforge import check, finding
from regforge.finding import Finding, Severity


def test_str_is_the_severity_then_the_message():
    assert (
        str(Finding(Severity.WARNING, "P.R: bit 1 is claimed")) == "warning: P.R: bit 1 is claimed"
    )
    assert str(Finding(Severity.ERROR, "P.R: past the end")) == "error: P.R: past the end"


def test_check_still_exports_the_same_classes():
    assert check.Finding is finding.Finding
    assert check.Severity is finding.Severity


def test_severity_values_are_the_words_the_log_prints():
    assert [severity.value for severity in Severity] == ["warning", "error"]

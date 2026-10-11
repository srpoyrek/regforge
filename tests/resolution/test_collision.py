"""CollisionResolution: the collision rule every level shares, shown here on another space.

The only real subclass today is the bit; the test subclass below occupies runs of offsets,
in hex, as an error. If the base were about bits it could not serve it.
"""

import inspect

from regforge.finding import Severity
from regforge.resolution import Collision, CollisionResolution, collision
from regforge.resolution.collision import merge


class _Span(CollisionResolution):
    """An element that occupies runs of offsets, written in hex; a collision is an error."""

    unit = "offset"
    severity = Severity.ERROR

    def __init__(self, owner, *ranges):
        super().__init__(owner, "P")
        self._ranges = list(ranges)

    @staticmethod
    def write(position):
        return f"{position:#x}"

    def ranges(self):
        return self._ranges

    def findings(self):
        return []


def _messages(findings):
    return [finding.message for finding in findings]


# --- comparing two elements ----------------------------------------------------------


def test_overlapping_runs_are_one_finding_in_the_words_of_the_space():
    (finding,) = _Span("A", (0x10, 0x13)).compare(_Span("B", (0x12, 0x1B)))
    assert finding.severity is Severity.ERROR
    assert finding.message == "P: offsets 0x12..0x13 are claimed by A and B"


def test_one_shared_position_is_named_in_the_singular():
    assert _messages(_Span("A", (0x0, 0x4)).compare(_Span("B", (0x4, 0x8)))) == [
        "P: offset 0x4 is claimed by A and B"
    ]


def test_runs_that_only_touch_do_not_collide():
    assert _Span("A", (0x0, 0x3)).compare(_Span("B", (0x4, 0x7))) == []


def test_runs_that_do_not_meet_do_not_collide():
    assert _Span("A", (0x0, 0x3)).compare(_Span("B", (0x10, 0x13))) == []


def test_an_unclaimed_element_collides_with_nothing():
    assert _Span(None, (0x0, 0x3)).compare(_Span("B", (0x0, 0x3))) == []
    assert _Span("A", (0x0, 0x3)).compare(_Span(None, (0x0, 0x3))) == []


def test_two_claimants_with_one_label_are_still_two():
    assert _messages(_Span("Reserved", (0x0, 0x3)).compare(_Span("Reserved", (0x2, 0x5)))) == [
        "P: offsets 0x2..0x3 are claimed by Reserved and Reserved"
    ]


def test_the_claimant_compared_is_named_first():
    assert _messages(_Span("B", (0x0, 0x0)).compare(_Span("A", (0x0, 0x0)))) == [
        "P: offset 0x0 is claimed by B and A"
    ]


def test_an_element_with_several_runs_collides_where_any_of_them_does():
    # An array: two runs. B sits across the gap and meets both.
    findings = _Span("A", (0x0, 0x1), (0x4, 0x5)).compare(_Span("B", (0x1, 0x4)))
    assert _messages(findings) == [
        "P: offset 0x1 is claimed by A and B",
        "P: offset 0x4 is claimed by A and B",
    ]


def test_pieces_that_touch_are_joined_into_one_run():
    findings = _Span("A", (0x0, 0x3), (0x4, 0x7)).compare(_Span("B", (0x2, 0x5)))
    assert _messages(findings) == ["P: offsets 0x2..0x5 are claimed by A and B"]


def test_a_collision_is_a_warning_unless_the_space_says_otherwise():
    class Plain(_Span):
        severity = CollisionResolution.severity

    (finding,) = Plain("A", (0, 1)).compare(Plain("B", (1, 2)))
    assert finding.severity is Severity.WARNING


# --- merging -------------------------------------------------------------------------


def test_merge_joins_touching_and_overlapping_collisions_of_one_pair():
    pieces = [
        Collision(4, 5, ("A", "B")),
        Collision(0, 1, ("A", "B")),
        Collision(2, 3, ("A", "B")),
        Collision(5, 7, ("A", "B")),
    ]
    assert merge(pieces) == [Collision(0, 7, ("A", "B"))]


def test_merge_keeps_collisions_of_different_pairs_apart():
    pieces = [Collision(0, 1, ("A", "B")), Collision(2, 3, ("A", "C"))]
    assert merge(pieces) == pieces


def test_merge_keeps_a_gap():
    pieces = [Collision(0, 1, ("A", "B")), Collision(3, 4, ("A", "B"))]
    assert merge(pieces) == pieces


def test_merge_of_nothing_is_nothing():
    assert merge([]) == []


def test_merge_does_not_change_what_it_is_given():
    pieces = [Collision(0, 1, ("A", "B")), Collision(2, 3, ("A", "B"))]
    merge(pieces)
    assert pieces == [Collision(0, 1, ("A", "B")), Collision(2, 3, ("A", "B"))]


# --- layering ----------------------------------------------------------------------


def test_the_shared_rule_knows_no_element():
    source = inspect.getsource(collision)
    assert "regforge.ir" not in source
    assert "Field" not in source and "Register" not in source

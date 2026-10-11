"""WriteConstraint: the values a register or field accepts when written."""

from regforge.ir import WriteConstraint


def test_a_new_constraint_constrains_nothing():
    constraint = WriteConstraint()
    assert constraint.write_as_read is None and constraint.use_enumerated_values is None
    assert constraint.minimum is None and constraint.maximum is None
    assert not constraint.has_range


def test_a_range_needs_both_ends():
    assert WriteConstraint(minimum=1, maximum=5).has_range
    assert not WriteConstraint(minimum=1).has_range
    assert not WriteConstraint(maximum=5).has_range


def test_in_range_accepts_the_ends_and_refuses_outside():
    constraint = WriteConstraint(minimum=1, maximum=5)
    assert [constraint.in_range(v) for v in (0, 1, 3, 5, 6)] == [False, True, True, True, False]


def test_without_a_range_every_number_is_in_range():
    assert WriteConstraint(use_enumerated_values=True).in_range(12345)
    assert WriteConstraint(write_as_read=True).in_range(-1)


def test_is_unconstrained_only_when_nothing_is_set():
    assert WriteConstraint().is_unconstrained
    assert WriteConstraint(write_as_read=False).is_unconstrained
    assert not WriteConstraint(write_as_read=True).is_unconstrained
    assert not WriteConstraint(use_enumerated_values=True).is_unconstrained
    assert not WriteConstraint(minimum=0, maximum=3).is_unconstrained

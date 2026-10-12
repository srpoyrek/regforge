"""The HTML wording of a write constraint."""

from __future__ import annotations

from regforge.ir import WriteConstraint
from regforge.writers.html.context import LeafHtml


class WriteConstraintHtml(LeafHtml):
    """Renders a :class:`~regforge.ir.WriteConstraint` as the notes on what may be written."""

    def notes(self, constraint: WriteConstraint | None) -> list[str]:
        """One note for each limit the constraint sets; none when there is no constraint."""
        if constraint is None:
            return []
        notes: list[str] = []
        if constraint.has_range:
            notes.append(f"valid values {constraint.minimum} to {constraint.maximum}")
        if constraint.use_enumerated_values:
            notes.append("only the listed values may be written")
        if constraint.write_as_read:
            notes.append("must be written back as it was read")
        return notes

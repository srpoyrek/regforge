"""The HTML wording of an array: how an element relates to its ``<dim>``."""

from __future__ import annotations

from regforge.ir import Cluster, Field, Peripheral, Register
from regforge.writers.html.context import LeafHtml


class DimHtml(LeafHtml):
    """Renders how an element relates to a ``<dim>`` array, as the note under its name."""

    def note(self, element: Peripheral | Cluster | Register | Field, unit: str) -> str | None:
        """How ``element`` relates to a ``<dim>`` array, or ``None`` for a plain element."""
        dim = element.dim
        if dim is not None and dim.array:
            return f"array of {dim.length}, {dim.stride:#x} {unit} apart"
        origin = element.origin
        if origin is not None:
            return f"copy {origin.index + 1} of {origin.count} of {origin.template}"
        return None

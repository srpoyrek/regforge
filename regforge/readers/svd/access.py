"""Reads the ``access`` child of an element."""

from __future__ import annotations

from regforge.ir import Access
from regforge.readers.svd.choice_parser import ChoiceParser


class AccessParser(ChoiceParser[Access]):
    """Reads ``<access>`` as a :class:`~regforge.ir.Access`."""

    kind = Access
    tag = "access"

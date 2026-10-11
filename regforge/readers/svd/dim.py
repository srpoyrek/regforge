"""Reads the ``<dim>`` group of an element."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from regforge.ir import Dim
from regforge.readers.svd.element_parser import ElementParser, ParseContext
from regforge.readers.svd.enumerated_value import EnumeratedValueParser
from regforge.readers.svd.primitives import child_int, child_text

_RANGE = re.compile(r"(\d+)-(\d+)|([A-Za-z])-([A-Za-z])")


def parse_dim_index(text: str, warnings: list[str] | None = None) -> list[str]:
    """Parse an SVD ``<dimIndex>`` into the labels that replace ``%s``.

    A comma-separated list of labels, any of which may be a numeric range
    (``0-3``) or a single-letter range (``A-D``); ``0-3,7`` mixes the forms.
    Whitespace around a label is dropped and both ends of a range are kept. A
    reversed range (``3-0``) is read ascending and noted in ``warnings``.
    """
    labels: list[str] = []
    for part in text.split(","):
        part = part.strip()
        match = _RANGE.fullmatch(part)
        if match is None:
            labels.append(part)
            continue
        if match.group(1) is not None:
            first, last = int(match.group(1)), int(match.group(2))
            if first > last:
                if warnings is not None:
                    warnings.append(f"dimIndex range {part} is reversed -- read as {last}-{first}")
                first, last = last, first
            labels += [str(i) for i in range(first, last + 1)]
        else:
            first, last = match.group(3), match.group(4)
            if first > last:
                if warnings is not None:
                    warnings.append(f"dimIndex range {part} is reversed -- read as {last}-{first}")
                first, last = last, first
            labels += [chr(code) for code in range(ord(first), ord(last) + 1)]
    return labels


class DimParser(ElementParser):
    """Reads the ``dim`` group: ``<dim>``, its increment, index, name and array index."""

    def __init__(self, context: ParseContext) -> None:
        super().__init__(context)
        self._value = EnumeratedValueParser()

    def parse(self, element: ET.Element, name: str, derived: bool = False) -> Dim | None:
        """Return the ``<dim>`` group of ``element``, or ``None`` when it has none.

        Only ``%s`` with no ``<dim>``, and a negative ``<dim>``, are refused here,
        like a field with no bit range. A ``<dim>`` of 0, or one with no
        ``<dimIncrement>``, is stored as read: expansion reports it and drops the
        element or keeps one instance. A ``<dimIncrement>`` with no ``<dim>`` is
        noted and ignored -- unless the element carries ``derivedFrom``, in which
        case a ``%s`` name, ``<dimIncrement>``, ``<dimIndex>`` or ``<dimName>`` with no
        ``<dim>`` is a partial ``Dim`` that expansion completes from the base
        template (``derived``). Labels are only parsed here; how
        many there are and whether they are usable names is judged by expansion,
        which can report at the element's path. The stride is not looked at: it
        needs the resolved register size, which exists only after defaults.
        """
        warnings = self.context.warnings
        count = child_int(element, "dim")
        if count is None:
            written = ("dimIncrement", "dimIndex", "dimName")
            if "%s" not in name and all(child_text(element, tag) is None for tag in written):
                return None
            if not derived:
                if child_text(element, "dimIncrement") is not None:
                    warnings.append(f"{name}: <dimIncrement> without <dim> -- ignored")
                if "%s" in name:
                    raise ValueError(f"{name!r} has a %s placeholder but no <dim>")
                return None
            # A derived element inherits what it leaves unsaid; the count comes
            # from the base template, in expansion's pre-pass.
        if count is not None and count < 0:
            raise ValueError(f"{name!r}: <dim> cannot be negative, got {count}")
        # A missing <dimIncrement> stays None: expansion reports it and keeps one
        # instance, since the copies' addresses are unknown.
        increment = child_int(element, "dimIncrement")
        index_text = child_text(element, "dimIndex")
        index = None
        if index_text is not None:
            notes: list[str] = []
            index = parse_dim_index(index_text, notes)
            warnings += [f"{name}: {note}" for note in notes]
        return Dim(
            count=count,
            increment=increment,
            index=index,
            name=child_text(element, "dimName"),
            array_index=self._value.parse_all(
                element, "./dimArrayIndex/enumeratedValue", numbered_only=True
            ),
        )

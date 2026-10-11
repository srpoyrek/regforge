"""What every stateful element parser shares: the context that collects warnings."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ParseContext:
    """State shared by one read of one file.

    Attributes:
        warnings: Notes about anything the parsers had to normalise on the way.
    """

    warnings: list[str] = field(default_factory=list)


class ElementParser:
    """Base of the parsers that can report a warning.

    A parser turns one XML element into the matching IR class and asks the parsers
    below it to build its children. Parsers with nothing to report need no context.
    """

    def __init__(self, context: ParseContext) -> None:
        self.context = context

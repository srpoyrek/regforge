"""The number formats and small helpers every HTML renderer shares.

What an element is worded as lives with the element: an access, a data type, a protection, the
reset values and what a write or a read does are leaves in the folder of the register that holds
them, the array note is a leaf of the peripheral. What stays here is formatting that belongs to
no element.
"""

from __future__ import annotations

NO_VALUE = "–"

#: Bits one hexadecimal digit stands for.
BITS_PER_HEX_DIGIT = 4

#: Characters of a description a summary table cell shows before it cuts the text.
SUMMARY_LIMIT = 90


def hex_digits(bits: int) -> int:
    """How many hexadecimal digits write a ``bits``-wide number in full."""
    return -(-bits // BITS_PER_HEX_DIGIT)


def hex_(value: int, digits: int) -> str:
    """``value`` as zero-padded upper-case hex, ``0x00FF``."""
    return f"0x{value:0{digits}X}"


def yes_no(value: bool) -> str:
    """``yes`` or ``no``."""
    return "yes" if value else "no"


def anchor(*parts: str) -> str:
    """An HTML id built from ``parts``."""
    return ".".join(parts).replace(" ", "_")


def short(text: str | None, limit: int = SUMMARY_LIMIT) -> str:
    """The first line of ``text``, cut to ``limit`` characters, for a summary table."""
    if not text or not text.strip():
        return ""
    first = text.strip().splitlines()[0].strip()
    return first if len(first) <= limit else first[: limit - 1].rstrip() + "…"

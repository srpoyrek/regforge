"""Reading primitives shared by every SVD element parser."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from enum import Enum, IntEnum
from typing import TypeVar, overload


class Radix(IntEnum):
    """Numeric bases accepted for SVD integer literals."""

    HEX = 16
    BINARY = 2
    DECIMAL = 10


def parse_svd_int(text: str) -> int:
    """Parse an SVD integer literal.

    Supports hexadecimal (``0x1F``), binary (``0b1010`` or ``#1010``), and
    decimal (``42``) notations as defined by the SVD schema.
    """
    token = text.strip().lower()
    if token.startswith("0x"):
        return int(token, Radix.HEX)
    if token.startswith("0b"):
        return int(token, Radix.BINARY)
    if token.startswith("#"):
        return int(token.removeprefix("#"), Radix.BINARY)
    return int(token, Radix.DECIMAL)


def parse_svd_bool(text: str) -> bool | None:
    """Parse an SVD boolean, accepting both ``true``/``false`` and ``1``/``0``.

    Some vendor files (Nordic, for example) write booleans as ``1``/``0``
    rather than ``true``/``false``; both spellings are normalized here.
    Anything unrecognized returns ``None`` so callers can treat it as absent.
    """
    token = text.strip().lower()
    if token in ("true", "1"):
        return True
    if token in ("false", "0"):
        return False
    return None


def child_text(element: ET.Element, tag: str) -> str | None:
    """Return the stripped text of ``element``'s ``tag`` child, or ``None``."""
    child = element.find(tag)
    if child is not None and child.text is not None:
        return child.text.strip()
    return None


@overload
def child_int(element: ET.Element, tag: str) -> int | None: ...
@overload
def child_int(element: ET.Element, tag: str, default: int) -> int: ...
def child_int(element: ET.Element, tag: str, default: int | None = None) -> int | None:
    """Return the integer value of ``element``'s ``tag`` child, or ``default``.

    Overloaded so a caller that passes an ``int`` default gets ``int`` back (not
    ``int | None``) -- so the parsed value can flow straight into an ``int`` field.
    """
    raw = child_text(element, tag)
    return parse_svd_int(raw) if raw is not None else default


def child_bool(element: ET.Element, tag: str) -> bool | None:
    """Return the boolean value of ``element``'s ``tag`` child, or ``None``."""
    raw = child_text(element, tag)
    return parse_svd_bool(raw) if raw is not None else None


E = TypeVar("E", bound=Enum)


def child_choice(element: ET.Element, tag: str, kind: type[E]) -> E | None:
    """Return ``element``'s ``tag`` child as a member of the closed vocabulary ``kind``.

    ``None`` when the child is absent or holds a spelling the schema does not list.
    """
    raw = child_text(element, tag)
    if raw is None:
        return None
    try:
        return kind(raw)
    except ValueError:
        return None

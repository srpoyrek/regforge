"""Placeholder names: the ``Reserved`` a vendor gives to everything it leaves unused.

A name that only marks something unused is not a clash when it repeats: a register has many
unused runs of bits and an enumerated set many unused numbers, and each is called ``Reserved``.
The elements that have names to repeat share this one test, and each says for itself whether it
is a placeholder.
"""

from __future__ import annotations

import re

#: ``reserved`` in any case, then optionally ``_`` and digits: ``Reserved``, ``RESERVED_``.
_PLACEHOLDER = re.compile(r"reserved[_0-9]*", re.IGNORECASE)


def is_placeholder_name(name: str) -> bool:
    """Whether ``name`` only marks something unused, so repeating it is not a clash.

    The name is ``reserved`` in any case, optionally followed by ``_`` or digits
    (``Reserved``, ``RESERVED_``, ``reserved3``). Anything else is a real name, and so is a
    longer one such as ``Reserved_BITS``.
    """
    return _PLACEHOLDER.fullmatch(name) is not None

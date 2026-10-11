"""The rules of each element of the register map: one class and one file per element.

A resolution class owns what is wrong with its element and says so in words, knowing only
its own level and the one below. Collisions, two claimants on one part of a space, are one
rule shared by every level that has them (:mod:`regforge.resolution.collision`), and so is the
placeholder name, ``Reserved``, which vendors repeat on purpose and no element reports as a
clash (:mod:`regforge.resolution.placeholder`).
:func:`collect` is the one place that knows the whole device: it hands each class the plain
data it needs and gathers everything they find into one list, which the command line
prints. Bits, fields, enumerated values, write behaviours and read actions come first; the
other elements still keep their rules in :mod:`regforge.check` and :mod:`regforge.resolve`.
"""

from regforge.resolution.base import Resolution as Resolution
from regforge.resolution.bit import BitResolution as BitResolution
from regforge.resolution.collector import collect as collect
from regforge.resolution.collision import Collision as Collision
from regforge.resolution.collision import CollisionResolution as CollisionResolution
from regforge.resolution.enum_set import EnumSetResolution as EnumSetResolution
from regforge.resolution.enum_usage import EnumUsageResolution as EnumUsageResolution
from regforge.resolution.enumerated_value import (
    EnumeratedValueResolution as EnumeratedValueResolution,
)
from regforge.resolution.field import FieldResolution as FieldResolution
from regforge.resolution.modified_write_values import (
    ModifiedWriteValuesResolution as ModifiedWriteValuesResolution,
)
from regforge.resolution.placeholder import is_placeholder_name as is_placeholder_name
from regforge.resolution.read_action import ReadActionResolution as ReadActionResolution

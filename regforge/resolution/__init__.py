"""The rules of each element of the register map: one class and one file per element.

A resolution class owns what is wrong with its element and says so in words, knowing only
its own level and the one below. Collisions, two claimants on one part of a space, are one
rule shared by every level that has them (:mod:`regforge.resolution.collision`), and so is the
placeholder name, ``Reserved``, which vendors repeat on purpose and no element reports as a
clash (:mod:`regforge.resolution.placeholder`).
:func:`collect` is the one place that knows the whole device: it hands each class the plain
data it needs and gathers everything they find into one list, which the command line
prints. Bits, fields, enumerated values, write behaviours, read actions, access and data
types come first; the other elements still keep their rules in :mod:`regforge.check` and
:mod:`regforge.resolve`.

The folders nest the way the elements do, and a class sits where the IR class whose rules it
holds sits (``regforge/ir/`` has the same tree), so the rules of what a device hands down
(``AccessResolution``) are in ``device/`` and those of a bit, a data type and what a write or a
read does are in ``register/``::

    resolution/
      base.py                  Resolution: what every class has in common
      collision.py             Collision, CollisionResolution: two claimants on one position
      placeholder.py           is_placeholder_name: ``Reserved`` and its kin
      collector.py             collect: the one place that knows the whole device
      device/                  AccessResolution
        peripheral/
          register/            BitResolution, DataTypeResolution, ModifiedWriteValuesResolution,
                               ReadActionResolution
            field/             FieldResolution
              enum_set/        EnumSetResolution, EnumUsageResolution, EnumeratedValueResolution

Everything is re-exported here, so the rest of regforge writes
``from regforge.resolution import FieldResolution`` and never needs to know where a class sits.
The tests mirror the tree under ``tests/resolution/``.
"""

from regforge.resolution.base import Resolution as Resolution
from regforge.resolution.collector import collect as collect
from regforge.resolution.collision import Collision as Collision
from regforge.resolution.collision import CollisionResolution as CollisionResolution
from regforge.resolution.device.access import AccessResolution as AccessResolution
from regforge.resolution.device.peripheral.register.bit import BitResolution as BitResolution
from regforge.resolution.device.peripheral.register.data_type import (
    DataTypeResolution as DataTypeResolution,
)
from regforge.resolution.device.peripheral.register.field.enum_set.enum_set import (
    EnumSetResolution as EnumSetResolution,
)
from regforge.resolution.device.peripheral.register.field.enum_set.enum_usage import (
    EnumUsageResolution as EnumUsageResolution,
)
from regforge.resolution.device.peripheral.register.field.enum_set.enumerated_value import (
    EnumeratedValueResolution as EnumeratedValueResolution,
)
from regforge.resolution.device.peripheral.register.field.field import (
    FieldResolution as FieldResolution,
)
from regforge.resolution.device.peripheral.register.modified_write_values import (
    ModifiedWriteValuesResolution as ModifiedWriteValuesResolution,
)
from regforge.resolution.device.peripheral.register.read_action import (
    ReadActionResolution as ReadActionResolution,
)
from regforge.resolution.placeholder import is_placeholder_name as is_placeholder_name

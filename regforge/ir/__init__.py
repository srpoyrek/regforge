"""Intermediate representation of a device register map.

The intermediate representation (IR) is the format-independent data model at
the centre of regforge. Input readers parse a source description into these
dataclasses, and output writers render them into a target language. Neither
side depends on the other: adding an input format or an output language only
touches its own package.

The hierarchy mirrors the structure of a memory-mapped device:

``Device`` -> ``Peripheral`` -> (``Cluster`` ->) ``AlternateSet`` -> ``Register`` -> ``Field``
-> ``EnumeratedValue``

An ``AlternateSet`` is one word of the register map: a set of one view for a plain
register, of several for registers that are different layouts of the same bits.

The folders nest the same way, and every module holds one class. A class sits in the folder of
the highest element that holds it, so the settings a device hands down (``Access``,
``Protection``) sit in ``device/`` and the arrays (``Dim``) in ``peripheral/``::

    ir/
      device/             Device, Cpu, Access, Protection
        peripheral/       Peripheral, AddressBlock, Interrupt, Dim, DimOrigin, ArrayGroup,
                          AlternateSet, RegistersOf
          cluster/        Cluster
          register/       Register, Bit, DataType, ModifiedWriteValues, ReadAction,
                          WriteConstraint
            field/        Field
              enum_set/   EnumSet, EnumeratedValue, EnumUsage

Everything is re-exported here, so the rest of regforge writes ``from regforge.ir import Field``
and never needs to know where a class sits. The tests mirror the tree under ``tests/ir/``.
"""

from regforge.ir.device.access import Access as Access
from regforge.ir.device.cpu import Cpu as Cpu
from regforge.ir.device.device import DEFAULT_ADDRESS_UNIT_BITS as DEFAULT_ADDRESS_UNIT_BITS
from regforge.ir.device.device import DEFAULT_BUS_WIDTH as DEFAULT_BUS_WIDTH
from regforge.ir.device.device import Device as Device
from regforge.ir.device.peripheral.address_block import BLOCK_BUFFER as BLOCK_BUFFER
from regforge.ir.device.peripheral.address_block import BLOCK_REGISTERS as BLOCK_REGISTERS
from regforge.ir.device.peripheral.address_block import BLOCK_RESERVED as BLOCK_RESERVED
from regforge.ir.device.peripheral.address_block import AddressBlock as AddressBlock
from regforge.ir.device.peripheral.alternate_set import AlternateSet as AlternateSet
from regforge.ir.device.peripheral.array_group import ArrayGroup as ArrayGroup
from regforge.ir.device.peripheral.array_group import array_groups as array_groups
from regforge.ir.device.peripheral.array_group import compact as compact
from regforge.ir.device.peripheral.cluster.cluster import Cluster as Cluster
from regforge.ir.device.peripheral.cluster.cluster import walk_clusters as walk_clusters
from regforge.ir.device.peripheral.dim import Dim as Dim
from regforge.ir.device.peripheral.dim_origin import DimOrigin as DimOrigin
from regforge.ir.device.peripheral.interrupt import Interrupt as Interrupt
from regforge.ir.device.peripheral.peripheral import Peripheral as Peripheral
from regforge.ir.device.peripheral.register.bit import Bit as Bit
from regforge.ir.device.peripheral.register.bit import bits as bits
from regforge.ir.device.peripheral.register.data_type import DataType as DataType
from regforge.ir.device.peripheral.register.field.enum_set.enum_set import EnumSet as EnumSet
from regforge.ir.device.peripheral.register.field.enum_set.enum_usage import EnumUsage as EnumUsage
from regforge.ir.device.peripheral.register.field.enum_set.enumerated_value import (
    EnumeratedValue as EnumeratedValue,
)
from regforge.ir.device.peripheral.register.field.field import Field as Field
from regforge.ir.device.peripheral.register.modified_write_values import (
    ModifiedWriteValues as ModifiedWriteValues,
)
from regforge.ir.device.peripheral.register.read_action import ReadAction as ReadAction
from regforge.ir.device.peripheral.register.register import Register as Register
from regforge.ir.device.peripheral.register.write_constraint import (
    WriteConstraint as WriteConstraint,
)
from regforge.ir.device.peripheral.registers_of import RegistersOf as RegistersOf
from regforge.ir.device.protection import Protection as Protection

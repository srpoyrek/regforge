"""CMSIS-SVD reader.

Parses a System View Description (SVD) file into the regforge intermediate
representation using only the Python standard library. One parser class per
element reads that element and hands its children to the parsers below it:
:class:`DeviceParser` calls :class:`PeripheralParser`, which calls
:class:`RegisterParser`, then :class:`FieldParser`, and so on down to the
vocabulary parsers. :class:`SvdReader` opens the file and starts at the top.

The folders nest the way the elements do, and a parser sits where the IR class it builds sits
(``regforge/ir/`` has the same tree), so the parsers of what a device hands down
(``AccessParser``, ``ProtectionParser``) are in ``device/`` and ``DimParser`` is in
``peripheral/``::

    svd/
      reader.py                SvdReader
      element_parser.py        ParseContext, ElementParser: what the parsers share
      choice_parser.py         ChoiceParser: the base of the closed-vocabulary parsers
      primitives.py            integers, booleans and child lookups
      device/                  DeviceParser, CpuParser, AccessParser, ProtectionParser
        peripheral/            PeripheralParser, AddressBlockParser, InterruptParser, DimParser
          cluster/             ClusterParser
          register/            RegisterParser, DataTypeParser, ModifiedWriteValuesParser,
                               ReadActionParser, WriteConstraintParser
            field/             FieldParser
              enum_set/        EnumSetParser, EnumUsageParser, EnumeratedValueParser

The tests mirror the tree under ``tests/readers/svd/``; the ones that read a whole file through
:class:`SvdReader` sit together in ``whole_file/``.

The reader accepts all three field bit-range encodings: ``bitOffset``/``bitWidth``,
``bitRange``, and ``lsb``/``msb``.

Notes:
    Inheritance (``derivedFrom``) and arrays (``dim``) are parsed, not
    expanded, by this reader: :mod:`regforge.resolve` does both. Clusters are
    walked, registers and nested clusters alike.
"""

from regforge.readers.svd.device.peripheral.dim import parse_dim_index as parse_dim_index
from regforge.readers.svd.primitives import Radix as Radix
from regforge.readers.svd.primitives import parse_svd_bool as parse_svd_bool
from regforge.readers.svd.primitives import parse_svd_int as parse_svd_int
from regforge.readers.svd.primitives import parse_svd_value as parse_svd_value
from regforge.readers.svd.reader import SvdReader as SvdReader

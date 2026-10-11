"""CMSIS-SVD reader.

Parses a System View Description (SVD) file into the regforge intermediate
representation using only the Python standard library. One parser class per
element reads that element and hands its children to the parsers below it:
:class:`DeviceParser` calls :class:`PeripheralParser`, which calls
:class:`RegisterParser`, then :class:`FieldParser`, and so on down to the
vocabulary parsers. :class:`SvdReader` opens the file and starts at the top.

The reader accepts all three field bit-range encodings: ``bitOffset``/``bitWidth``,
``bitRange``, and ``lsb``/``msb``.

Notes:
    Inheritance (``derivedFrom``) and arrays (``dim``) are parsed, not
    expanded, by this reader: :mod:`regforge.resolve` does both. Clusters are
    walked, registers and nested clusters alike.
"""

from regforge.readers.svd.dim import parse_dim_index as parse_dim_index
from regforge.readers.svd.primitives import Radix as Radix
from regforge.readers.svd.primitives import parse_svd_bool as parse_svd_bool
from regforge.readers.svd.primitives import parse_svd_int as parse_svd_int
from regforge.readers.svd.reader import SvdReader as SvdReader

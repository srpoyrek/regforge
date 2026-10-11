"""The rules of each element of the register map: one class and one file per element.

A resolution class owns what is wrong with its element and says so in words, knowing only
its own level. :func:`collect` is the one place that knows the whole device: it hands each
class the plain data it needs and gathers everything they find into one list, which the
command line prints. Bits come first; the other elements still keep their rules in
:mod:`regforge.check` and :mod:`regforge.resolve`.
"""

from regforge.resolution.base import Resolution as Resolution
from regforge.resolution.bit import BitResolution as BitResolution
from regforge.resolution.collector import collect as collect

"""DimHtml: how an element relates to its ``<dim>`` array."""

from regforge.ir import Cluster, Dim, DimOrigin, Field, Peripheral, Register
from regforge.writers.html.device.peripheral.dim import DimHtml


def test_a_kept_array_says_how_many_and_how_far_apart():
    kept = Register("A", 0x0, dim=Dim(4, 4, array=True))
    assert DimHtml().note(kept, "units") == "array of 4, 0x4 units apart"


def test_an_unrolled_copy_says_which_one_it_is():
    copy = Register("D0", 0x0, origin=DimOrigin("D%s", Dim(2, 4), 0, "0"))
    assert DimHtml().note(copy, "units") == "copy 1 of 2 of D%s"


def test_a_plain_element_has_no_note():
    for element in (Register("R", 0x0), Peripheral("P", 0x0), Cluster("C", 0x0), Field("F", 0, 1)):
        assert DimHtml().note(element, "units") is None


def test_the_unit_is_the_one_the_caller_names():
    field = Field("OD", 0, 1, dim=Dim(4, 2, array=True))
    assert DimHtml().note(field, "bits") == "array of 4, 0x2 bits apart"


def test_it_serves_every_element_that_can_be_an_array():
    peripheral = Peripheral("P", 0x0, dim=Dim(2, 4, array=True))
    cluster = Cluster("C", 0x0, dim=Dim(2, 4, array=True))
    assert DimHtml().note(peripheral, "units") == "array of 2, 0x4 units apart"
    assert DimHtml().note(cluster, "units") == "array of 2, 0x4 units apart"

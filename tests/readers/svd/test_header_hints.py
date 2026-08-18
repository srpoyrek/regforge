"""Layer 1: headerDefinitionsPrefix parsing and vendorExtensions preservation."""

from regforge.readers.svd import SvdReader


def test_header_prefix_parsed(tmp_path):
    svd = tmp_path / "p.svd"
    svd.write_text(
        "<device><name>X</name>" "<headerDefinitionsPrefix>NRF_</headerDefinitionsPrefix></device>",
        encoding="utf-8",
    )
    assert SvdReader().read(svd).header_prefix == "NRF_"


def test_header_prefix_absent_is_none(tmp_path):
    svd = tmp_path / "p.svd"
    svd.write_text("<device><name>X</name></device>", encoding="utf-8")
    assert SvdReader().read(svd).header_prefix is None


def test_vendor_extensions_preserved_verbatim(tmp_path):
    svd = tmp_path / "v.svd"
    svd.write_text(
        "<device><name>X</name><vendorExtensions>"
        "<esp:soc xmlns:esp='urn:esp'>secret</esp:soc>"
        "</vendorExtensions></device>",
        encoding="utf-8",
    )
    blob = SvdReader().read(svd).vendor_extensions_xml
    assert blob is not None
    # The opaque subtree is kept, not interpreted.
    assert "secret" in blob


def test_vendor_extensions_absent_is_none(tmp_path):
    svd = tmp_path / "v.svd"
    svd.write_text("<device><name>X</name></device>", encoding="utf-8")
    assert SvdReader().read(svd).vendor_extensions_xml is None

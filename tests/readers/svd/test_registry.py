"""SVD reader registration and discovery."""

import pytest

from regforge.readers import available_readers, get_reader, reader_for_path
from regforge.readers.svd import SvdReader


def test_svd_reader_is_registered():
    assert "svd" in available_readers()
    assert isinstance(get_reader("svd"), SvdReader)


def test_reader_inferred_from_extension(minimal_svd_path):
    assert isinstance(reader_for_path(minimal_svd_path), SvdReader)


def test_unknown_format_raises():
    with pytest.raises(ValueError):
        get_reader("does-not-exist")


def test_unknown_extension_raises():
    with pytest.raises(ValueError):
        reader_for_path("device.unknown")

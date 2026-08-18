"""Tests for the writer registry and the C writer."""

import pytest

from regforge.writers import available_writers, get_writer, writer_for_path
from regforge.writers.c import CWriter


def test_c_writer_is_registered():
    assert "c" in available_writers()
    assert isinstance(get_writer("c"), CWriter)


def test_writer_inferred_from_extension():
    assert isinstance(writer_for_path("device.h"), CWriter)


def test_unknown_target_raises():
    with pytest.raises(ValueError):
        get_writer("does-not-exist")


def test_render_matches_golden(demo_device, golden_header_path):
    generated = CWriter().render(demo_device)
    assert generated == golden_header_path.read_text(encoding="utf-8")

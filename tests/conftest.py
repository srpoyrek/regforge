"""Shared pytest fixtures."""

from pathlib import Path

import pytest

from regforge.ir import Device
from regforge.readers.svd import SvdReader

TESTS_DIR = Path(__file__).parent


@pytest.fixture
def minimal_svd_path() -> Path:
    """Path to the minimal SVD fixture."""
    return TESTS_DIR / "svd" / "minimal.svd"


@pytest.fixture
def golden_header_path() -> Path:
    """Path to the golden C header for the minimal fixture."""
    return TESTS_DIR / "golden" / "minimal.h"


@pytest.fixture
def demo_device(minimal_svd_path: Path) -> Device:
    """The device parsed from the minimal SVD fixture."""
    return SvdReader().read(minimal_svd_path)

"""Shared fixtures for the test suite.

Fixtures defined here are available to every test in every subfolder
(readers/, writers/, core/, cli/). Input fixtures live under fixtures/ and
golden output under golden/<language>/.
"""

from pathlib import Path

import pytest

from regforge.ir import Device
from regforge.readers.svd import SvdReader
from regforge.resolve import resolve_defaults

TESTS_DIR = Path(__file__).parent
MINIMAL_SVD = TESTS_DIR / "fixtures" / "svd" / "minimal.svd"
GOLDEN_C = TESTS_DIR / "golden" / "c" / "minimal.h"


@pytest.fixture
def minimal_svd_path() -> Path:
    """Path to the minimal SVD input fixture."""
    return MINIMAL_SVD


@pytest.fixture
def golden_header_path() -> Path:
    """Path to the golden C header for the minimal fixture."""
    return GOLDEN_C


@pytest.fixture
def demo_device() -> Device:
    """The device parsed from the minimal SVD fixture, defaults resolved."""
    device = SvdReader().read(MINIMAL_SVD)
    resolve_defaults(device)
    return device

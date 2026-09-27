"""Shared fixtures for the test suite.

Fixtures defined here are available to every test in every subfolder
(readers/, writers/, core/, cli/). Input fixtures live under fixtures/ and
golden output under golden/<language>/.
"""

from pathlib import Path

import pytest

from regforge.ir import Device
from regforge.readers.svd import SvdReader
from regforge.resolve import expand_dim, resolve_defaults, resolve_derived

TESTS_DIR = Path(__file__).parent
MINIMAL_SVD = TESTS_DIR / "fixtures" / "svd" / "minimal.svd"
GOLDEN_C = TESTS_DIR / "golden" / "c" / "minimal.h"
LINT_DEMO_SVD = TESTS_DIR / "fixtures" / "svd" / "lint_demo.svd"
LINT_DEMO_GOLDEN = TESTS_DIR / "golden" / "c" / "lint_demo.h"


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
    """The device parsed from the minimal SVD fixture, expanded and resolved."""
    device = SvdReader().read(MINIMAL_SVD)
    expand_dim(device)
    resolve_derived(device)
    resolve_defaults(device)
    return device


@pytest.fixture
def lint_demo_svd_path() -> Path:
    """Path to the deliberately-flawed SVD that trips every consistency check."""
    return LINT_DEMO_SVD


@pytest.fixture
def lint_demo_golden_path() -> Path:
    """Path to the golden C header for the flawed lint-demo fixture."""
    return LINT_DEMO_GOLDEN


@pytest.fixture
def lint_demo_device() -> Device:
    """The flawed lint-demo device, expanded and resolved."""
    device = SvdReader().read(LINT_DEMO_SVD)
    expand_dim(device)
    resolve_derived(device)
    resolve_defaults(device)
    return device

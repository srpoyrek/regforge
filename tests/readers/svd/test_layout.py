"""The layout of the SVD reader: it has the tree of the IR, and its tests sit in the mirror.

A parser sits in the folder where the IR class it builds sits, device > peripheral > register >
field > enumerated set (a cluster beside the register, inside the peripheral), so the reader and
the IR have one shape and the place of a parser tells where its test is. Only the modules the
parsers share -- the reader, the element and choice parsers, the primitives -- stay at the top.
"""

import importlib
import inspect
from pathlib import Path

import pytest

READER = Path(__file__).resolve().parents[3] / "regforge" / "readers" / "svd"
IR = READER.parents[1] / "ir"
MIRROR = Path(__file__).resolve().parent
#: The elements that contain one another, from the top down.
CHAIN = ("device", "peripheral", "register", "field", "enum_set")
#: What the parsers share; these stay at the top of the tree.
SHARED = {"reader", "element_parser", "choice_parser", "primitives"}


def _modules() -> list[Path]:
    return [path for path in sorted(READER.rglob("*.py")) if path.name != "__init__.py"]


def _parsers() -> list[Path]:
    return [path for path in _modules() if path.parent != READER]


def _name(path: Path) -> str:
    relative = path.relative_to(READER.parents[2]).with_suffix("")
    return ".".join(relative.parts)


def _classes(path: Path) -> list[type]:
    module = importlib.import_module(_name(path))
    return [
        cls
        for name, cls in inspect.getmembers(module, inspect.isclass)
        if cls.__module__ == module.__name__ and not name.startswith("_")
    ]


def _test_name(path: Path) -> str:
    """``test_<stem>_parser.py`` for a parser; a shared module is tested as ``test_<stem>.py``."""
    shared = path.parent == READER
    return f"test_{path.stem}.py" if shared else f"test_{path.stem}_parser.py"


def _ids(path: Path) -> str:
    return path.relative_to(READER).with_suffix("").as_posix()


def test_the_folders_nest_as_the_elements_contain_one_another():
    folder = READER
    for element in CHAIN:
        folder = folder / element
        assert (folder / "__init__.py").is_file(), f"{element} has no folder inside its parent's"


def test_the_cluster_sits_beside_the_register_inside_the_peripheral():
    assert (READER / "device" / "peripheral" / "cluster" / "__init__.py").is_file()


def test_only_the_shared_modules_sit_at_the_top():
    top = {path.stem for path in READER.glob("*.py") if path.name != "__init__.py"}
    assert top == SHARED


@pytest.mark.parametrize("path", _parsers(), ids=_ids)
def test_a_parser_sits_where_the_ir_class_it_builds_sits(path):
    twin = IR / path.relative_to(READER)
    assert twin.is_file(), f"{path} has no counterpart {twin} in the IR"


@pytest.mark.parametrize("path", _modules(), ids=_ids)
def test_every_module_has_its_test_in_the_mirrored_folder(path):
    folder = MIRROR / path.parent.relative_to(READER)
    assert (folder / _test_name(path)).is_file(), f"no {_test_name(path)} for {path} in {folder}"


@pytest.mark.parametrize("path", _parsers(), ids=_ids)
def test_a_parser_module_holds_at_most_one_public_class(path):
    assert len(_classes(path)) <= 1, [cls.__name__ for cls in _classes(path)]


def test_the_top_of_the_mirror_holds_only_the_tests_of_the_shared_modules():
    top = {path.name for path in MIRROR.glob("test_*.py")}
    assert top == {f"test_{stem}.py" for stem in SHARED} | {"test_layout.py"}

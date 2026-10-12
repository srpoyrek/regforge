"""The layout of the resolution classes: the tree of the IR, and their tests in the mirror.

A resolution class sits in the folder where the IR class whose rules it holds sits, device >
peripheral > register > field > enumerated set, so the rules and the IR have one shape and the
place of a class tells where its test is. Only the modules the classes share -- the base, the
collision rule, the placeholder test and the collector -- stay at the top.
"""

import importlib
import inspect
from pathlib import Path

import pytest

RESOLUTION = Path(__file__).resolve().parents[2] / "regforge" / "resolution"
IR = RESOLUTION.parent / "ir"
MIRROR = Path(__file__).resolve().parent
#: The elements that contain one another, from the top down.
CHAIN = ("device", "peripheral", "register", "field", "enum_set")
#: What the classes share; these stay at the top of the tree.
SHARED = {"base", "collision", "placeholder", "collector"}


def _modules() -> list[Path]:
    return [path for path in sorted(RESOLUTION.rglob("*.py")) if path.name != "__init__.py"]


def _rules() -> list[Path]:
    """The modules that hold the rules of one element: all but the shared ones at the top."""
    return [path for path in _modules() if path.parent != RESOLUTION]


def _name(path: Path) -> str:
    relative = path.relative_to(RESOLUTION.parents[1]).with_suffix("")
    return ".".join(relative.parts)


def _classes(path: Path) -> list[type]:
    module = importlib.import_module(_name(path))
    return [
        cls
        for name, cls in inspect.getmembers(module, inspect.isclass)
        if cls.__module__ == module.__name__ and not name.startswith("_")
    ]


def _test_name(path: Path) -> str:
    """``test_<stem>_resolution.py`` for a class; a shared module is ``test_<stem>.py``."""
    shared = path.parent == RESOLUTION
    return f"test_{path.stem}.py" if shared else f"test_{path.stem}_resolution.py"


def _ids(path: Path) -> str:
    return path.relative_to(RESOLUTION).with_suffix("").as_posix()


def test_the_folders_nest_as_the_elements_contain_one_another():
    folder = RESOLUTION
    for element in CHAIN:
        folder = folder / element
        assert (folder / "__init__.py").is_file(), f"{element} has no folder inside its parent's"


def test_only_the_shared_modules_sit_at_the_top():
    top = {path.stem for path in RESOLUTION.glob("*.py") if path.name != "__init__.py"}
    assert top == SHARED


@pytest.mark.parametrize("path", _rules(), ids=_ids)
def test_a_resolution_class_sits_where_the_ir_class_it_judges_sits(path):
    twin = IR / path.relative_to(RESOLUTION)
    assert twin.is_file(), f"{path} has no counterpart {twin} in the IR"


@pytest.mark.parametrize("path", _modules(), ids=_ids)
def test_every_module_has_its_test_in_the_mirrored_folder(path):
    folder = MIRROR / path.parent.relative_to(RESOLUTION)
    assert (folder / _test_name(path)).is_file(), f"no {_test_name(path)} for {path} in {folder}"


@pytest.mark.parametrize("path", _rules(), ids=_ids)
def test_a_module_holds_at_most_one_public_class(path):
    assert len(_classes(path)) <= 1, [cls.__name__ for cls in _classes(path)]


def test_the_top_of_the_mirror_holds_only_the_tests_of_the_shared_modules():
    top = {path.name for path in MIRROR.glob("test_*.py")}
    assert top == {f"test_{stem}.py" for stem in SHARED} | {"test_layout.py"}

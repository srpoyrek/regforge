"""The layout of the IR: folders nest as the elements do, tests sit in the mirror.

The classes sit in folders that nest the way the elements contain one another, device >
peripheral > register > field > enumerated set (a cluster beside the register, inside the
peripheral), each class in the folder of the highest element that holds it. The tests mirror the
tree one file for each module, so the place of a class tells where its test is.
"""

import importlib
import inspect
from pathlib import Path

import pytest

import regforge.ir as ir

IR = Path(__file__).resolve().parents[2] / "regforge" / "ir"
MIRROR = Path(__file__).resolve().parent
#: The elements that contain one another, from the top down.
CHAIN = ("device", "peripheral", "register", "field", "enum_set")


def _modules() -> list[Path]:
    return [path for path in sorted(IR.rglob("*.py")) if path.name != "__init__.py"]


def _name(path: Path) -> str:
    relative = path.relative_to(IR.parent.parent).with_suffix("")
    return ".".join(relative.parts)


def _classes(path: Path) -> list[type]:
    module = importlib.import_module(_name(path))
    return [
        cls
        for name, cls in inspect.getmembers(module, inspect.isclass)
        if cls.__module__ == module.__name__ and not name.startswith("_")
    ]


def _ids(path: Path) -> str:
    return _name(path).split("ir.", 1)[1]


def test_the_folders_nest_as_the_elements_contain_one_another():
    folder = IR
    for element in CHAIN:
        folder = folder / element
        assert (folder / "__init__.py").is_file(), f"{element} has no folder inside its parent's"


def test_the_cluster_sits_beside_the_register_inside_the_peripheral():
    assert (IR / "device" / "peripheral" / "cluster" / "__init__.py").is_file()


@pytest.mark.parametrize("path", _modules(), ids=_ids)
def test_every_module_has_its_test_in_the_mirrored_folder(path):
    folder = MIRROR / path.parent.relative_to(IR)
    assert (folder / f"test_{path.stem}.py").is_file(), f"no test for {path} in {folder}"


@pytest.mark.parametrize("path", _modules(), ids=_ids)
def test_a_module_holds_at_most_one_public_class(path):
    assert len(_classes(path)) <= 1, [cls.__name__ for cls in _classes(path)]


def test_the_package_exports_every_class_of_every_module():
    for path in _modules():
        for cls in _classes(path):
            assert (
                getattr(ir, cls.__name__) is cls
            ), f"{cls.__name__} is not exported by regforge.ir"

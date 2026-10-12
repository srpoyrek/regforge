"""The layout of the HTML writer: folders nest as the elements do, tests sit in the mirror.

The renderers sit in folders that nest the way the elements contain one another, device >
peripheral > register > field > enumerated set, each element's folder inside its parent's. The
tests mirror that tree one file for each module, so the place of a class tells where its test is.
"""

import importlib
import inspect
from pathlib import Path

import pytest

from regforge.writers.html.context import ElementHtml, LeafHtml

HTML = Path(__file__).resolve().parents[3] / "regforge" / "writers" / "html"
MIRROR = Path(__file__).resolve().parent
#: The modules of the writer itself, which belong to no element.
THE_WRITER = {"context", "wording", "writer"}
#: The elements that contain one another, from the top down.
CHAIN = ("device", "peripheral", "register", "field", "enum_set")


def _modules() -> list[Path]:
    return [
        path
        for path in sorted(HTML.rglob("*.py"))
        if path.name != "__init__.py" and not (path.parent == HTML and path.stem in THE_WRITER)
    ]


def _name(path: Path) -> str:
    relative = path.relative_to(HTML.parent.parent.parent).with_suffix("")
    return ".".join(relative.parts)


def _renderers(path: Path) -> list[type]:
    module = importlib.import_module(_name(path))
    return [
        cls
        for _, cls in inspect.getmembers(module, inspect.isclass)
        if cls.__module__ == module.__name__ and issubclass(cls, (ElementHtml, LeafHtml))
    ]


def test_the_folders_nest_as_the_elements_contain_one_another():
    folder = HTML
    for element in CHAIN:
        folder = folder / element
        assert (folder / "__init__.py").is_file(), f"{element} has no folder inside its parent's"


@pytest.mark.parametrize("path", _modules(), ids=lambda path: _name(path).split("html.", 1)[1])
def test_every_module_has_its_test_in_the_mirrored_folder(path):
    folder = MIRROR / path.parent.relative_to(HTML)
    candidates = [folder / f"test_{path.stem}_html.py", folder / f"test_{path.stem}.py"]
    assert any(c.is_file() for c in candidates), f"no test for {path} in {folder}"


@pytest.mark.parametrize("path", _modules(), ids=lambda path: _name(path).split("html.", 1)[1])
def test_a_module_holds_at_most_one_renderer(path):
    assert len(_renderers(path)) <= 1


def test_every_class_named_for_html_is_a_block_or_a_leaf():
    for path in _modules():
        module = importlib.import_module(_name(path))
        for name, cls in inspect.getmembers(module, inspect.isclass):
            if cls.__module__ == module.__name__ and name.endswith("Html"):
                assert issubclass(cls, (ElementHtml, LeafHtml)), name


def test_a_leaf_is_built_on_its_own_and_a_block_needs_the_environment():
    for path in _modules():
        for cls in _renderers(path):
            required = [
                p
                for p in inspect.signature(cls).parameters.values()
                if p.default is inspect.Parameter.empty
            ]
            if issubclass(cls, LeafHtml):
                assert not required, f"{cls.__name__} is a leaf, but needs {required}"
            else:
                assert len(required) == 1, f"{cls.__name__} is a block: it takes the context"

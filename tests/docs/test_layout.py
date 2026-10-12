"""The layout of the rule pages: they nest as the elements do, and what they name exists.

A rule page sits in the folder of the highest element it is about, the folder that element's IR
class sits in: device > peripheral > register > field > enumerated set, a cluster beside the
register. The pages of the two sides of the pipeline, an input format and an output target, stay
in their own folders. Two things rot silently when files move: a page missing from the
navigation, and a path on a ``Code:`` or ``Tests:`` line that is no longer there.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
RULES = DOCS / "rules"
#: The elements that contain one another, from the top down.
CHAIN = ("device", "peripheral", "register", "field", "enum_set")
#: The folders of the pipeline's two sides; their pages are not about an element.
SIDES = ("formats", "targets")
#: Where a rule page may sit: the chain, one folder deeper each time, and the cluster beside it.
FOLDERS = [CHAIN[: depth + 1] for depth in range(len(CHAIN))] + [CHAIN[:2] + ("cluster",)]


def _pages() -> list[Path]:
    return sorted(DOCS.rglob("*.md"))


def _rule_pages() -> list[Path]:
    """The pages that state a rule: all of rules/ but the index and the two sides."""
    return [
        page
        for page in sorted(RULES.rglob("*.md"))
        if page.name != "README.md" and page.relative_to(RULES).parts[0] not in SIDES
    ]


def _ids(page: Path) -> str:
    return page.relative_to(DOCS).as_posix()


def _named_paths(page: Path) -> list[str]:
    """The repository paths a page names in its ``Code:`` and ``Tests:`` paragraphs."""
    found: list[str] = []
    for paragraph in page.read_text(encoding="utf-8").split("\n\n"):
        if paragraph.startswith(("Code:", "Tests:")):
            found += re.findall(r"`((?:regforge|tests)/[^`\s]*)`", paragraph)
    return found


def test_the_folders_nest_as_the_elements_contain_one_another():
    folder = RULES
    for element in CHAIN:
        folder = folder / element
        assert list(folder.glob("*.md")), f"{element} has no page in its parent's folder"


def test_the_cluster_sits_beside_the_register_inside_the_peripheral():
    assert list((RULES / "device" / "peripheral" / "cluster").glob("*.md"))


@pytest.mark.parametrize("page", _rule_pages(), ids=_ids)
def test_a_rule_page_sits_in_the_folder_of_an_element(page):
    folders = page.relative_to(RULES).parts[:-1]
    assert folders in FOLDERS, f"{_ids(page)} is not in an element's folder"


@pytest.mark.parametrize("page", _rule_pages(), ids=_ids)
def test_a_rule_page_says_where_its_code_and_tests_are(page):
    text = page.read_text(encoding="utf-8")
    assert "Code:" in text and "Tests:" in text, f"{_ids(page)} names no code or no tests"


@pytest.mark.parametrize("page", _pages(), ids=_ids)
def test_every_path_a_page_names_exists(page):
    missing = [path for path in _named_paths(page) if not (ROOT / path).exists()]
    assert not missing, f"{_ids(page)} names paths that are not there: {missing}"


@pytest.mark.parametrize("page", _pages(), ids=_ids)
def test_every_page_is_in_the_navigation(page):
    navigation = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    assert _ids(page) in navigation, f"{_ids(page)} is not in mkdocs.yml"

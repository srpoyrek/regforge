"""The rule documentation is checked like code.

Two things rot silently: links break when files move, and examples drift when
behaviour changes. Both are verified here so neither can happen unnoticed.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

DOCS = Path(__file__).resolve().parents[2] / "docs"
RULES = DOCS / "rules"


def _pages() -> list[Path]:
    return sorted(DOCS.rglob("*.md"))


def _anchors(path: Path) -> set[str]:
    """GitHub-style heading anchors for one page."""
    found = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        heading = re.match(r"^#{1,6}\s+(.*?)\s*$", line)
        if heading is None:
            continue
        text = re.sub(r"`([^`]*)`", r"\1", heading.group(1))
        text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
        found.add(re.sub(r"[^\w\s-]", "", text.lower()).strip().replace(" ", "-"))
    return found


def test_every_link_resolves():
    # Covers both halves: the file has to exist, and the heading it points at
    # has to exist in that file. Moving a page or renaming a section fails here
    # rather than leaving a link that goes nowhere.
    broken: list[str] = []
    anchors: dict[Path, set[str]] = {}
    for page in _pages():
        for link in re.findall(r"\]\(([^)]+?)\)", page.read_text(encoding="utf-8")):
            if link.startswith("http"):
                continue
            file_part, _, fragment = link.partition("#")
            target = page if not file_part else (page.parent / file_part)
            if not target.exists():
                broken.append(f"{page.name} -> {link} (no such file)")
                continue
            if fragment:
                anchors.setdefault(target, _anchors(target))
                if fragment not in anchors[target]:
                    broken.append(f"{page.name} -> {link} (no such heading)")
    assert not broken, "broken documentation links:\n  " + "\n  ".join(broken)


def test_every_rule_page_routes_to_a_format_and_a_target():
    # A rule page describes a decision, not a file format or a language. Each one
    # must say where its input is read and where its output is spelled, so adding
    # a format or a target is a matter of following those links.
    missing: list[str] = []
    for page in sorted(RULES.glob("*.md")):
        if page.name == "README.md":
            continue
        text = page.read_text(encoding="utf-8")
        if "formats/" not in text:
            missing.append(f"{page.name}: no link to an input format")
        if "targets/" not in text:
            missing.append(f"{page.name}: no link to an output target")
    assert not missing, "rule pages must route to both sides:\n  " + "\n  ".join(missing)


def _worked_examples(page: Path, fence: str) -> dict[str, str]:
    """Every ``### heading`` in the Worked examples section, with its code block."""
    text = page.read_text(encoding="utf-8")
    if "## Worked examples" not in text:
        return {}
    section = text.split("## Worked examples", 1)[1]
    blocks: dict[str, str] = {}
    for chunk in section.split("\n### ")[1:]:
        title = chunk.split("\n", 1)[0].strip()
        match = re.search(rf"```{fence}\n(.*?)```", chunk, re.S)
        if match:
            blocks[title] = match.group(1)
    return blocks


def test_worked_examples_are_paired():
    # Each example is documented from both sides. One without the other means a
    # reader can see the input but not the result, or the reverse.
    svd = _worked_examples(RULES / "formats" / "svd.md", "xml")
    emitted = _worked_examples(RULES / "targets" / "c.md", "c")
    assert svd, "no worked examples found on the SVD page"
    assert set(svd) == set(emitted), (
        f"unpaired worked examples: only in SVD {sorted(set(svd) - set(emitted))}, "
        f"only in C {sorted(set(emitted) - set(svd))}"
    )


def test_worked_examples_match_what_regforge_generates(tmp_path):
    # The documented output is regenerated from the documented input. If
    # behaviour changes and the docs are not updated, this fails and names the
    # example -- so the docs cannot quietly describe an older regforge.
    pytest.importorskip("jinja2")
    from regforge.readers.svd import SvdReader
    from regforge.resolve import resolve_defaults, resolve_derived
    from regforge.writers.c import CWriter

    svd = _worked_examples(RULES / "formats" / "svd.md", "xml")
    emitted = _worked_examples(RULES / "targets" / "c.md", "c")
    stale: list[str] = []
    for title, source in svd.items():
        path = tmp_path / "example.svd"
        path.write_text(source, encoding="utf-8")
        device = SvdReader().read(path)
        resolve_derived(device)
        resolve_defaults(device)
        generated = CWriter().render(device)
        for line in emitted[title].splitlines():
            if line.strip() and line.strip() not in generated:
                stale.append(f"{title}: {line.strip()}")
    assert not stale, "documented output no longer matches regforge:\n  " + "\n  ".join(stale)

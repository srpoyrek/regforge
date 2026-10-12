"""Wording: the number formats and small helpers every HTML renderer shares.

What an element is worded as is tested beside the element, in the folder that mirrors the
renderer's own (see ``test_layout.py``).
"""

from regforge.writers.html.wording import anchor, hex_, hex_digits, short, yes_no


def test_hex_is_zero_padded_upper_case():
    assert hex_(255, 4) == "0x00FF"


def test_hex_digits_round_up_to_a_whole_digit():
    assert [hex_digits(b) for b in (0, 1, 4, 5, 8, 32, 64)] == [0, 1, 1, 2, 2, 8, 16]


def test_anchor_joins_parts_and_removes_spaces():
    assert anchor("P", "CH.CTRL") == "P.CH.CTRL"
    assert anchor("a b") == "a_b"


def test_short_takes_the_first_line_and_cuts_a_long_one():
    assert short(None) == "" and short("   ") == ""
    assert short("first line\nsecond line") == "first line"
    cut = short("x" * 200, limit=20)
    assert len(cut) == 20 and cut.endswith("…")


def test_yes_no_spells_a_flag():
    assert yes_no(True) == "yes" and yes_no(False) == "no"

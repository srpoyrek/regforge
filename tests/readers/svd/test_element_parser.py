"""ParseContext and ElementParser: what every stateful parser shares."""

from regforge.readers.svd.element_parser import ElementParser, ParseContext


def test_a_context_starts_with_no_warnings():
    assert ParseContext().warnings == []


def test_two_contexts_do_not_share_one_warning_list():
    assert ParseContext().warnings is not ParseContext().warnings


def test_a_parser_keeps_the_context_it_was_given():
    context = ParseContext()
    assert ElementParser(context).context is context

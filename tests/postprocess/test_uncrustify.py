"""Post-processing: uncrustify availability and language guards.

These monkeypatch `shutil.which` so they behave identically whether or not
uncrustify is actually installed on the host.
"""

import pytest

from regforge import postprocess
from regforge.postprocess import FormatterNotAvailable, uncrustify, uncrustify_available


def test_missing_binary_raises(monkeypatch):
    monkeypatch.setattr(postprocess.shutil, "which", lambda name: None)
    assert uncrustify_available() is False
    with pytest.raises(FormatterNotAvailable):
        uncrustify("int x;\n")


def test_unsupported_language_raises(monkeypatch):
    # Pretend uncrustify is installed so the language check is what fails.
    monkeypatch.setattr(postprocess.shutil, "which", lambda name: "/usr/bin/uncrustify")
    with pytest.raises(ValueError, match="does not support language"):
        uncrustify("print()\n", language="Python")

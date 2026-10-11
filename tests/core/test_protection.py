"""Protection: the security level an access needs."""

import pytest

from regforge.ir import Protection


def test_values_are_spelled_as_in_svd():
    assert [p.value for p in Protection] == ["s", "n", "p"]


def test_each_value_maps_back_to_its_member():
    assert Protection("s") is Protection.SECURE
    assert Protection("n") is Protection.NON_SECURE
    assert Protection("p") is Protection.PRIVILEGED


def test_an_unknown_spelling_is_refused():
    with pytest.raises(ValueError):
        Protection("x")


def test_each_value_says_what_it_requires():
    assert [p for p in Protection if p.requires_secure] == [Protection.SECURE]
    assert [p for p in Protection if p.allows_non_secure] == [Protection.NON_SECURE]
    assert [p for p in Protection if p.requires_privilege] == [Protection.PRIVILEGED]

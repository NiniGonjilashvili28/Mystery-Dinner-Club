"""Tests for login tokens."""
from tokens import make_token, read_token


def test_a_token_gives_back_its_user_id():
    assert read_token("secret", make_token("secret", 7)) == 7


def test_a_token_signed_with_another_key_is_rejected():
    assert read_token("secret", make_token("other-secret", 7)) is None


def test_an_edited_token_is_rejected():
    token = make_token("secret", 7)
    assert read_token("secret", token[:-2] + "xx") is None


def test_a_missing_token_is_rejected():
    assert read_token("secret", None) is None
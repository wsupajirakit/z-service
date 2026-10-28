"""AUTH_SECRET has no fallback: missing or short means no session works and no boot."""

import re

import pytest

from zservice.security import tokens as auth


def test_token_round_trip_with_a_real_secret(env):
    env(AUTH_SECRET="s" * 40)
    token = auth.create_token("me")
    assert auth.decode_token(token)["sub"] == "me"


@pytest.mark.parametrize("value", ["", "short-secret", "x" * 27])
def test_missing_or_short_secret_fails_closed(value, env):
    env(AUTH_SECRET="s" * 40)
    token = auth.create_token("me")
    env(AUTH_SECRET=value)
    assert auth.decode_token(token) is None  # every session is rejected
    with pytest.raises(RuntimeError):
        auth.create_token("me")
    with pytest.raises(RuntimeError):
        auth.assert_configured()


def test_a_28_character_secret_is_enough(env):
    env(AUTH_SECRET="k" * 28)
    auth.assert_configured()
    assert auth.decode_token(auth.create_token("me"))["sub"] == "me"


def test_token_signed_with_another_secret_is_rejected(env):
    env(AUTH_SECRET="a" * 40)
    token = auth.create_token("me")
    env(AUTH_SECRET="b" * 40)
    assert auth.decode_token(token) is None


def test_the_old_hardcoded_fallback_is_gone():
    from zservice.security import tokens

    with open(tokens.__file__, encoding="utf-8") as f:
        source = f.read()
    # An empty default is fine; a non-empty literal default would be a usable secret.
    assert not re.search(r'environ\.get\("AUTH_SECRET",\s*"[^"]+"', source)

import json

import pytest

from zservice.security.machine import BASE64_PREFIX, KEY_PATTERN, hash_secret, load_keys

SECRET = "A" * 43
GOOD = {
    "id": "home",
    "name": "home mac",
    "scopes": ["read", "jobs"],
    "sha256": hash_secret(SECRET),
    "expires": "2027-04-22",
}


def _raw(*entries):
    return json.dumps(list(entries))


def test_empty_config_means_no_keys():
    assert load_keys(None) == {}
    assert load_keys("  ") == {}


def test_parses_a_valid_entry():
    key = load_keys(_raw(GOOD))["home"]
    assert key.scopes == frozenset({"read", "jobs"})
    assert key.expires.isoformat() == "2027-04-22"


@pytest.mark.parametrize(
    "patch",
    [
        {"scopes": ["read", "root"]},  # unknown scope
        {"scopes": []},  # empty scopes
        {"sha256": "abc"},  # not a sha256
        {"id": "a/b"},  # bad id
    ],
)
def test_rejects_bad_entries(patch):
    with pytest.raises(ValueError):
        load_keys(_raw({**GOOD, **patch}))


def test_rejects_duplicate_ids_and_non_list():
    with pytest.raises(ValueError):
        load_keys(_raw(GOOD, GOOD))
    with pytest.raises(ValueError):
        load_keys(json.dumps(GOOD))


def test_key_pattern():
    assert KEY_PATTERN.match(f"zsk_home_{SECRET}")
    assert not KEY_PATTERN.match(f"zsk_home_{'A' * 10}")  # secret too short
    assert not KEY_PATTERN.match(f"pk_home_{SECRET}")


def test_base64_form_survives_panels_that_strip_quotes():
    import base64

    plain = _raw(GOOD)
    encoded = BASE64_PREFIX + base64.b64encode(plain.encode()).decode()
    assert '"' not in encoded
    assert load_keys(encoded) == load_keys(plain)


def test_stripped_quotes_and_bad_base64_name_the_variable():
    stripped = _raw(GOOD).replace('"', "")
    with pytest.raises(ValueError, match=r"ZS_API_KEYS is not valid JSON.*base64"):
        load_keys(stripped)
    with pytest.raises(ValueError, match=r"ZS_API_KEYS: the base64: value does not decode"):
        load_keys(BASE64_PREFIX + "not base64!")

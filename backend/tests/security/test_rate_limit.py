import pytest

from zservice.security.rate_limit import SlidingWindow


def test_allows_up_to_limit_then_blocks_until_window_passes():
    w = SlidingWindow(limit=2, window_s=10)
    assert w.hit("k", now=0) is None
    assert w.hit("k", now=1) is None
    assert w.hit("k", now=2) == 9
    assert w.hit("k", now=10.5) is None  # first hit aged out


def test_keys_are_independent():
    w = SlidingWindow(limit=1, window_s=10)
    assert w.hit("a", now=0) is None
    assert w.hit("b", now=0) is None


def test_rejects_nonsense_config():
    with pytest.raises(ValueError):
        SlidingWindow(limit=0, window_s=10)

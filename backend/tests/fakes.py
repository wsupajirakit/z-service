"""Shared test helpers for faking the data layer."""


def swap_repos(monkeypatch, module, fake) -> None:
    """Point every repository a module imported (`<name>_repo` aliases, as the code base
    imports them) at one in-memory fake that implements the functions the test needs."""
    names = [n for n in vars(module) if n.endswith("_repo")]
    assert names, f"{module.__name__} imports no repository"
    for name in names:
        monkeypatch.setattr(module, name, fake)

"""The process-wide MachineAuth instance.

Built once from env at first use (main.py touches it at import, so a malformed
ZS_API_KEYS stops the boot instead of failing open). Tests swap it with `use()`.
"""

from .auth import MachineAuth, from_env


class _Holder:
    def __init__(self) -> None:
        self.auth: MachineAuth | None = None


_holder = _Holder()


def current() -> MachineAuth:
    if _holder.auth is None:
        _holder.auth = from_env()
    return _holder.auth


def use(auth: MachineAuth) -> None:
    """Replace the instance (tests, or a reload after rotating keys)."""
    _holder.auth = auth

"""Typed configuration from the environment (pydantic-settings).

Each domain declares the variables it reads in its own Settings class — name, type,
default and bounds in one place (fastapi-best-practices: "decouple BaseSettings" per
domain). No other module reads os.environ; tools/check_structure.py enforces it.

* `bootstrap.load_env()` has already merged .env / .env.local into os.environ, so the
  classes read the process environment only (no env_file of their own).
* `settings_getter(cls)` returns a cached accessor: the environment is read once per
  process, on first use.
* `validate_all()` runs at app start-up and builds every registered class, so a
  malformed value stops the boot with the variable named instead of failing a request.
* `reset()` drops the caches (tests change the environment between cases).
* A blank value means "use the default", as before. Secrets are SecretStr, so a repr or a
  log line shows '**********'.
"""

import functools
from collections.abc import Callable
from typing import Annotated, Any

from pydantic import AliasChoices, BeforeValidator, Field
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class ZsSettings(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore",
        env_ignore_empty=True,
        frozen=True,
        str_strip_whitespace=True,
    )


def env_field(name: str, default: Any, *fallbacks: str, doc: str, **constraints: Any) -> Any:
    """A field read from env `name` (then any legacy `fallbacks`). The name is spelled out
    in full so every variable can be found by grep; `doc` is its line in
    docs/config-reference.md (tools/config_reference.py)."""
    alias = AliasChoices(name, *fallbacks) if fallbacks else name
    return Field(default, validation_alias=alias, description=doc, **constraints)


def env_names(cls: type[BaseSettings]) -> list[str]:
    """The variables a Settings class reads (primary names, then legacy fallbacks)."""
    names = []
    for field in cls.model_fields.values():
        alias = field.validation_alias
        names += alias.choices if isinstance(alias, AliasChoices) else [alias]
    return [str(n) for n in names]


def _split_commas(value):
    if isinstance(value, str):
        return tuple(part.strip() for part in value.split(",") if part.strip())
    return value


# A comma-separated env value ("a, b,c") as a tuple of non-empty, stripped parts.
CommaList = Annotated[tuple[str, ...], NoDecode, BeforeValidator(_split_commas)]

_GETTERS: list[Callable[[], ZsSettings]] = []


def settings_getter[S: ZsSettings](cls: type[S]) -> Callable[[], S]:
    """Cached accessor for one Settings class, registered for validate_all / reset."""
    getter = functools.cache(cls)
    _GETTERS.append(getter)
    return getter


def registered() -> list[type[ZsSettings]]:
    return [getter.__wrapped__ for getter in _GETTERS]


def validate_all() -> None:
    for getter in _GETTERS:
        getter()


def reset() -> None:
    for getter in _GETTERS:
        getter.cache_clear()

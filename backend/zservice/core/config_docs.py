"""docs/config-reference.md, rendered from the Settings classes (tools/config_reference.py
writes it; a test fails when it is stale), so the list of variables cannot drift from the
code that reads them."""

import importlib
import inspect
import pkgutil

import annotated_types
from pydantic import AliasChoices, SecretStr
from pydantic.fields import FieldInfo

from zservice.core import config

PACKAGES = ("zservice", "radar_engine")
HEADER = """# Configuration reference

Generated from the Settings classes by `tools/config_reference.py`; do not edit by hand.
Every variable the backend reads is listed here. A blank value means the default, and a
malformed one stops the boot with the variable named. Production values are set in
Coolify (docs/runbook-deploy.md); secrets are never printed.
"""


def discover() -> list[type[config.ZsSettings]]:
    """Import every module of the backend packages, then return the registered classes."""
    for name in PACKAGES:
        package = importlib.import_module(name)
        for module in pkgutil.walk_packages(package.__path__, f"{name}."):
            importlib.import_module(module.name)
    return sorted(config.registered(), key=lambda c: (c.__module__, c.__name__))


def render(classes: list[type[config.ZsSettings]]) -> str:
    parts = [HEADER]
    for cls in classes:
        summary = (inspect.getdoc(inspect.getmodule(cls)) or "").splitlines()[0]
        parts.append(f"\n## {cls.__name__} (`{cls.__module__}`)\n\n{summary}\n")
        parts.append("\n| Variable | Type | Default | Description |\n|---|---|---|---|\n")
        parts += [_row(field) for field in cls.model_fields.values()]
    return "".join(parts)


def _row(field: FieldInfo) -> str:
    alias = field.validation_alias
    names = list(alias.choices) if isinstance(alias, AliasChoices) else [alias]
    variable = f"`{names[0]}`" + "".join(f" (legacy `{n}`)" for n in names[1:])
    return f"| {variable} | {_type(field)} | {_default(field)} | {field.description} |\n"


def _type(field: FieldInfo) -> str:
    text = field.annotation.__name__ if isinstance(field.annotation, type) else ""
    if "SecretStr" in str(field.annotation):
        return "secret"
    if "tuple" in str(field.annotation):
        return "comma list"
    bounds = {annotated_types.Gt: ">", annotated_types.Ge: "≥"}
    for meta in field.metadata:
        for kind, sign in bounds.items():
            if isinstance(meta, kind):
                bound = meta.gt if kind is annotated_types.Gt else meta.ge
                text += f" {sign} {bound}"
    return text


def _default(field: FieldInfo) -> str:
    value = field.default
    if isinstance(value, SecretStr):
        value = value.get_secret_value()
    if value in ("", (), None):
        return "—"
    return f"`{str(value).lower() if isinstance(value, bool) else value}`"

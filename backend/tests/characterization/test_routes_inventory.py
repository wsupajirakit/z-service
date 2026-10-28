"""Every HTTP route (method, path, parameters, request-body fields) must survive the move
out of main.py.

Built from the app's own OpenAPI document rather than `app.routes`: FastAPI 0.138 wraps
included routers in an internal `_IncludedRouter`, so walking `app.routes` silently skips
every router-mounted route (gold, radar_round, admin, health). OpenAPI is the public
contract and covers them all.
"""

from .golden import check

_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}


def _resolve(schema: dict, components: dict) -> dict:
    ref = schema.get("$ref")
    return components[ref.rsplit("/", 1)[-1]] if ref else schema


def _body_contract(op: dict, components: dict) -> dict | None:
    """Request-body fields (name -> type, required). The model class name is not pinned,
    so models can be renamed or moved without a false alarm."""
    content = op.get("requestBody", {}).get("content", {})
    if not content:
        return None
    schema = _resolve(next(iter(content.values()))["schema"], components)
    required = set(schema.get("required", []))
    return {
        name: {"type": prop.get("type") or prop.get("anyOf"), "required": name in required}
        for name, prop in sorted(schema.get("properties", {}).items())
    }


def _inventory(app) -> list[dict]:
    spec = app.openapi()
    components = spec.get("components", {}).get("schemas", {})
    routes = []
    for path, ops in spec["paths"].items():
        for method, op in ops.items():
            if method not in _METHODS:
                continue
            params = sorted(
                (p["in"], p["name"], bool(p.get("required"))) for p in op.get("parameters", [])
            )
            routes.append(
                {
                    "method": method.upper(),
                    "path": path,
                    "params": [list(p) for p in params],
                    "body": _body_contract(op, components),
                }
            )
    return sorted(routes, key=lambda r: (r["path"], r["method"]))


def test_route_inventory_is_unchanged(main_module):
    check("routes", _inventory(main_module.app))


def test_main_is_only_the_app_entry(main_module):
    # uvicorn runs `main:app`; everything else is imported from the zservice package.
    public = {n for n in vars(main_module) if not n.startswith("_")}
    assert public == {"app", "bootstrap", "create_app"}, sorted(public)

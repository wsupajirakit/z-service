"""Portfolio ledger (moved unchanged from main.py). `summarize` is pure for testing."""

from zservice.core.clock import now_iso
from zservice.db.repos import portfolio as portfolio_repo


def summarize(rows: list[dict]) -> dict[str, dict]:
    """{port_name: {"positions": [...open positions...], "history": [...all rows...]}}.

    Average price = net cost / net quantity over buy (+) and sell (-) rows, rounded to 2
    decimals; symbols with net quantity <= 0 are not listed as positions.
    """
    portfolios: dict[str, dict] = {}
    totals: dict[str, dict[str, dict]] = {}
    for r in rows:
        port = r["port_name"]
        data = portfolios.setdefault(port, {"positions": [], "history": []})
        data["history"].append(
            {
                "symbol": r["symbol"],
                "quantity": r["quantity"],
                "buy_price": r["buy_price"],
                "timestamp": r["timestamp"],
                "action": r["action"],
            }
        )
        t = totals.setdefault(port, {}).setdefault(r["symbol"], {"qty": 0, "cost": 0.0})
        sign = {"buy": 1, "sell": -1}.get(r["action"], 0)
        t["qty"] += sign * r["quantity"]
        t["cost"] += sign * r["quantity"] * r["buy_price"]
    for port, symbols in totals.items():
        for sym, t in symbols.items():
            if t["qty"] > 0:
                portfolios[port]["positions"].append(
                    {
                        "symbol": sym,
                        "total_quantity": t["qty"],
                        "avg_price": round(t["cost"] / t["qty"], 2),
                    }
                )
    return portfolios


def all_portfolios() -> dict[str, dict]:
    return summarize(portfolio_repo.portfolio_all())


def add(port_name: str, symbol: str, quantity: int, buy_price: float, action: str) -> None:
    portfolio_repo.portfolio_add(port_name, symbol, quantity, buy_price, now_iso(), action)


def remove_symbol(port_name: str, symbol: str) -> None:
    portfolio_repo.portfolio_remove(port_name, symbol)


def rename(port_name: str, new_name: str) -> None:
    portfolio_repo.portfolio_rename(port_name, new_name)

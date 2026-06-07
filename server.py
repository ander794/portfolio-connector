"""
Portfolio Insights — a Claude connector (MCP Apps server).

Exposes portfolio financial data as MCP tools and ships an interactive,
embeddable UI (the "MCP App") that Claude renders inline in the conversation
and can expand to fullscreen — the same pattern Spotify / Booking connectors use.

Data is mock/sample data so the server is fully self-contained and free to run.
Swap `PORTFOLIOS` for a real data source (brokerage API, DB) later without
touching the UI contract.

Run locally:
    pip install -r requirements.txt
    uvicorn server:app --host 0.0.0.0 --port 8000
Connector URL for Claude:  http://localhost:8000/mcp
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

# --------------------------------------------------------------------------- #
# Transport security (DNS-rebinding protection)
# --------------------------------------------------------------------------- #
# By default the Streamable HTTP transport only trusts a localhost Host header,
# so a hosted deployment (e.g. portfolio-connector.onrender.com) gets rejected
# with "Invalid Host header" / HTTP 421. DNS-rebinding protection primarily
# guards *localhost-bound* dev servers, so for a public server behind a platform
# TLS proxy we open it up. Set MCP_ALLOWED_HOSTS to harden:
#   MCP_ALLOWED_HOSTS="portfolio-connector.onrender.com"  (comma-separated)


def _transport_security() -> TransportSecuritySettings:
    raw = os.environ.get("MCP_ALLOWED_HOSTS", "").strip()
    if not raw or raw == "*":
        # Open: accept any Host (works on Render, Cloudflare, tunnels, locally).
        return TransportSecuritySettings(enable_dns_rebinding_protection=False)
    hosts = {h.strip() for h in raw.split(",") if h.strip()}
    hosts |= {"localhost", "127.0.0.1", "localhost:*", "127.0.0.1:*"}
    origins = {f"https://{h}" for h in hosts if not h.startswith(("localhost", "127."))}
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=sorted(hosts),
        allowed_origins=sorted(origins),
    )


# --------------------------------------------------------------------------- #
# Server
# --------------------------------------------------------------------------- #

mcp = FastMCP(
    "Portfolio Insights",
    instructions=(
        "Provides financial information for the user's investment portfolios. "
        "Call `show_portfolio` to render an interactive portfolio card the user "
        "can expand to fullscreen. Call `list_portfolios` to enumerate available "
        "portfolios first if the user hasn't named one."
    ),
    transport_security=_transport_security(),
)

# The ui:// scheme tells Claude this resource is an MCP App (interactive view).
VIEW_URI = "ui://portfolio-insights/portfolio.html"

# Load the embedded view once at startup.
EMBEDDED_VIEW_HTML = (Path(__file__).parent / "views" / "portfolio.html").read_text(
    encoding="utf-8"
)

# --------------------------------------------------------------------------- #
# Mock data — replace with a real provider to go live
# --------------------------------------------------------------------------- #

# Raw holdings: shares, last price, and average cost basis per share.
PORTFOLIOS: dict[str, dict] = {
    "growth": {
        "name": "Growth Portfolio",
        "currency": "USD",
        # 30 most-recent total-value points for the sparkline (oldest -> newest)
        "sparkline": [
            112.1, 113.4, 111.9, 114.8, 116.2, 115.0, 117.6, 119.1, 118.3, 120.9,
            122.4, 121.0, 123.8, 125.1, 124.0, 126.7, 128.0, 127.2, 129.9, 131.1,
            130.0, 132.6, 134.2, 133.1, 135.8, 137.0, 136.1, 138.9, 140.2, 141.5,
        ],
        "holdings": [
            # ticker, name, sector, shares, price, cost_basis, day_change_pct
            ("AAPL", "Apple Inc.", "Technology", 120, 214.30, 151.20, 0.82),
            ("NVDA", "NVIDIA Corp.", "Technology", 60, 132.10, 48.50, 2.41),
            ("MSFT", "Microsoft Corp.", "Technology", 45, 472.55, 305.10, 0.34),
            ("AMZN", "Amazon.com Inc.", "Consumer Disc.", 50, 219.80, 138.00, -0.61),
            ("TSLA", "Tesla Inc.", "Consumer Disc.", 40, 248.40, 205.70, -1.95),
            ("LLY", "Eli Lilly & Co.", "Healthcare", 18, 902.10, 612.30, 1.12),
        ],
    },
    "income": {
        "name": "Dividend Income",
        "currency": "USD",
        "sparkline": [
            98.0, 98.4, 98.1, 99.0, 99.3, 99.1, 99.8, 100.2, 100.0, 100.6,
            100.9, 100.5, 101.2, 101.6, 101.3, 101.9, 102.1, 101.8, 102.4, 102.7,
            102.5, 103.0, 103.3, 103.1, 103.7, 104.0, 103.8, 104.3, 104.6, 104.9,
        ],
        "holdings": [
            ("JNJ", "Johnson & Johnson", "Healthcare", 80, 158.20, 149.40, 0.21),
            ("KO", "Coca-Cola Co.", "Consumer Staples", 200, 70.10, 58.30, 0.45),
            ("PG", "Procter & Gamble", "Consumer Staples", 90, 168.90, 142.10, 0.12),
            ("VZ", "Verizon Comms.", "Communications", 150, 43.60, 51.20, -0.33),
            ("O", "Realty Income", "Real Estate", 120, 58.40, 62.00, 0.08),
            ("XOM", "Exxon Mobil", "Energy", 110, 118.70, 96.50, 0.74),
        ],
    },
}


def _build_payload(portfolio_id: str) -> dict:
    """Compute the full UI/model payload for one portfolio from raw holdings."""
    raw = PORTFOLIOS[portfolio_id]

    holdings = []
    total_value = 0.0
    total_cost = 0.0
    day_change_value = 0.0

    for ticker, name, sector, shares, price, cost_basis, day_pct in raw["holdings"]:
        value = shares * price
        cost = shares * cost_basis
        prev_price = price / (1 + day_pct / 100)
        day_change_value += shares * (price - prev_price)
        total_value += value
        total_cost += cost
        holdings.append(
            {
                "ticker": ticker,
                "name": name,
                "sector": sector,
                "shares": shares,
                "price": round(price, 2),
                "value": round(value, 2),
                "costBasis": round(cost_basis, 2),
                "dayChangePct": round(day_pct, 2),
                "gainPct": round((price - cost_basis) / cost_basis * 100, 2),
                "gainValue": round(value - cost, 2),
            }
        )

    # weights + sector allocation
    for h in holdings:
        h["weight"] = round(h["value"] / total_value * 100, 1)

    allocation: dict[str, float] = {}
    for h in holdings:
        allocation[h["sector"]] = allocation.get(h["sector"], 0.0) + h["weight"]
    allocation_list = sorted(
        ({"sector": s, "weight": round(w, 1)} for s, w in allocation.items()),
        key=lambda a: a["weight"],
        reverse=True,
    )

    total_gain = total_value - total_cost
    prev_total = total_value - day_change_value

    return {
        "id": portfolio_id,
        "name": raw["name"],
        "currency": raw["currency"],
        "asOf": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "totalValue": round(total_value, 2),
        "dayChange": round(day_change_value, 2),
        "dayChangePct": round(day_change_value / prev_total * 100, 2),
        "totalGain": round(total_gain, 2),
        "totalGainPct": round(total_gain / total_cost * 100, 2),
        "sparkline": raw["sparkline"],
        "holdings": sorted(holdings, key=lambda h: h["value"], reverse=True),
        "allocation": allocation_list,
        # ids of every portfolio so the fullscreen view can offer a switcher
        "available": [
            {"id": pid, "name": p["name"]} for pid, p in PORTFOLIOS.items()
        ],
    }


# --------------------------------------------------------------------------- #
# UI resource — the embeddable view (served to Claude's sandboxed iframe)
# --------------------------------------------------------------------------- #


@mcp.resource(
    VIEW_URI,
    mime_type="text/html;profile=mcp-app",
    # CSP: allow loading the ext-apps client from esm.sh inside the sandbox.
    meta={"ui": {"csp": {"resourceDomains": ["https://esm.sh"]}}},
)
def portfolio_view() -> str:
    """The interactive portfolio view rendered inline / fullscreen by Claude."""
    return EMBEDDED_VIEW_HTML


# --------------------------------------------------------------------------- #
# Typed output models
# --------------------------------------------------------------------------- #
# A typed return value is REQUIRED for FastMCP to emit `structuredContent` in the
# tool result. Claude only mounts the MCP App (interactive view) when the result
# carries structuredContent; with a plain `dict` return it ships text only and the
# view never renders. These models mirror the shape built by `_build_payload`.


class Holding(BaseModel):
    ticker: str
    name: str
    sector: str
    shares: float
    price: float
    value: float
    costBasis: float
    dayChangePct: float
    gainPct: float
    gainValue: float
    weight: float = 0.0


class Allocation(BaseModel):
    sector: str
    weight: float


class AvailablePortfolio(BaseModel):
    id: str
    name: str


class Portfolio(BaseModel):
    id: str
    name: str
    currency: str
    asOf: str
    totalValue: float
    dayChange: float
    dayChangePct: float
    totalGain: float
    totalGainPct: float
    sparkline: list[float]
    holdings: list[Holding]
    allocation: list[Allocation]
    available: list[AvailablePortfolio]


# --------------------------------------------------------------------------- #
# Tools
# --------------------------------------------------------------------------- #


@mcp.tool()
def list_portfolios() -> dict:
    """List the available investment portfolios with their headline value.

    Use this when the user hasn't specified which portfolio they mean.
    """
    items = []
    for pid in PORTFOLIOS:
        p = _build_payload(pid)
        items.append(
            {
                "id": p["id"],
                "name": p["name"],
                "totalValue": p["totalValue"],
                "dayChangePct": p["dayChangePct"],
                "currency": p["currency"],
            }
        )
    return {"portfolios": items}


@mcp.tool(
    meta={
        # Links this tool's result to the interactive view above.
        "ui": {"resourceUri": VIEW_URI},
        "ui/resourceUri": VIEW_URI,  # legacy key, kept for older hosts
    }
)
def show_portfolio(portfolio_id: str = "growth") -> Portfolio:
    """Show an interactive financial overview of a portfolio.

    Renders an embedded card (total value, day change, top holdings, sparkline)
    that the user can expand to a fullscreen view with the full holdings table
    and sector allocation. Pass a `portfolio_id` from `list_portfolios`
    (e.g. "growth" or "income"); defaults to the growth portfolio.
    """
    if portfolio_id not in PORTFOLIOS:
        valid = ", ".join(PORTFOLIOS)
        raise ValueError(f"Unknown portfolio '{portfolio_id}'. Available: {valid}")
    return Portfolio.model_validate(_build_payload(portfolio_id))


# --------------------------------------------------------------------------- #
# ASGI app for hosting (Streamable HTTP transport, endpoint: /mcp)
# --------------------------------------------------------------------------- #

app = mcp.streamable_http_app()


# Lightweight health/landing routes so platform probes to "/" don't 404.
async def _health(request):  # noqa: ANN001
    from starlette.responses import JSONResponse

    return JSONResponse({"status": "ok", "service": "portfolio-insights", "mcp": "/mcp"})


app.add_route("/", _health, methods=["GET", "HEAD"])
app.add_route("/healthz", _health, methods=["GET", "HEAD"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
        log_level="info",
    )

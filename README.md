# Portfolio Insights — a Claude connector

A Claude **connector** (remote MCP server) that shows financial information for
investment portfolios as an **interactive embedded view** — the same
Spotify / Booking-style experience: Claude renders a portfolio card inline in the
conversation, and the user can **tap "Expand" to open a fullscreen view** with the
full holdings table and sector allocation.

Built on the [MCP Apps extension](https://modelcontextprotocol.io/extensions/apps/overview)
(`text/html;profile=mcp-app` UI resources + tool `_meta.ui.resourceUri`).
Data is **mock/sample data**, so the whole thing runs for free with no API keys.

## What's in here

| File | Purpose |
|------|---------|
| `server.py` | MCP server: `list_portfolios` + `show_portfolio` tools, and the UI resource |
| `views/portfolio.html` | The embedded interactive view (inline card + fullscreen), self-contained |
| `requirements.txt` | Python deps (`mcp`, `uvicorn`) |
| `Dockerfile` / `render.yaml` | Free container deploy |
| `DEPLOY.md` | **Step-by-step: deploy this connector for free** |

## How it works

1. `show_portfolio` is a normal MCP tool, but its `_meta.ui.resourceUri` points at
   the `ui://portfolio-insights/portfolio.html` resource.
2. When Claude calls the tool, it fetches that resource and renders the HTML in a
   sandboxed iframe, pushing the tool's structured result into the view.
3. The view reads the data (`app.ontoolresult`), draws the inline card, and the
   **Expand** button calls `app.requestDisplayMode({ mode: "fullscreen" })`.
4. In fullscreen the user gets the holdings table, sector-allocation bars, and a
   portfolio switcher that calls `show_portfolio` again via `app.callServerTool`.

## Run locally

```bash
uv venv --python 3.10 .venv && source .venv/bin/activate   # Python 3.10+ required
uv pip install -r requirements.txt
python server.py            # serves http://localhost:8000/mcp
```

To try it inside Claude, expose it with a tunnel and add it as a custom connector —
see **[DEPLOY.md](DEPLOY.md)**.

## Test locally (3 ways)

**1. Tools & data — MCP Inspector** (confirms the server, no UI render):
```bash
python server.py                          # terminal 1
npx @modelcontextprotocol/inspector       # terminal 2 → Streamable HTTP, http://localhost:8000/mcp
```

**2. Render the real embedded view — ext-apps basic-host** (sandboxed iframe + live tool calls):
```bash
git clone https://github.com/modelcontextprotocol/ext-apps.git
cd ext-apps/examples/basic-host && npm install
SERVERS='["http://localhost:8000/mcp"]' npm start    # open http://localhost:8080
```

**3. Instant UI preview — `dev-preview.html`** (mocks the host bridge with real sample data;
see both the inline card and fullscreen view in a browser, no host or paid plan needed):
```bash
python3 -m http.server 5500                # from the project dir
# open http://localhost:5500/dev-preview.html
```
Must be served over HTTP (not opened as a `file://`) — the harness `fetch()`es the view.
Toggle "Inline card" / "Fullscreen", and the view's own Expand/Minimize and portfolio
switcher all work. This is a dev-only file; it isn't part of the deployed server.

**4. End-to-end in Claude** — tunnel + custom connector, see [DEPLOY.md](DEPLOY.md).

## Editing the interactive view

The view is built from `ui/` and **bundled into a single self-contained
`views/portfolio.html`** (the official `@modelcontextprotocol/ext-apps` SDK is
inlined — no CDN, so it renders inside Claude's CSP-sandboxed iframe). To change it:

```bash
cd ui
npm install        # first time only
# edit ui/src/mcp-app.js (logic) or ui/mcp-app.html (markup/CSS)
npm run build      # regenerates ../views/portfolio.html
```

`views/portfolio.html` is the committed build output the server serves, so
**deployment stays pure-Python** — Render just serves the bundled file, no Node
build needed in the container. Only re-run `npm run build` when you edit the view.

## Make it real

Replace the `PORTFOLIOS` dict and `_build_payload()` in `server.py` with calls to a
brokerage / market-data API. The UI contract (the JSON shape returned by
`show_portfolio`) is all the view depends on, so the front-end doesn't change.

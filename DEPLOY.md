# Deploy this Claude connector — for free

This is the checklist to get **Portfolio Insights** running as a live Claude
connector without paying for hosting. Pick **one** hosting option (A, B, or C),
then do the **"Add it to Claude"** step at the bottom.

---

## 0. Prerequisites (read first)

- [ ] **A paid Claude plan (Pro, Max, or Team).** Custom connectors are *only*
      available on paid plans — this is an Anthropic restriction, not a cost of
      this project. The free Claude tier cannot add custom connectors.
- [ ] **A public `https://` URL ending in `/mcp`.** Claude will not connect to
      `http://` or `localhost`. Every option below gives you HTTPS for free.
- [ ] **Python 3.10+** if running locally (the MCP SDK needs 3.10+; your system
      `python3` is 3.9 — use `python3.10`, already installed via Homebrew, or `uv`).
- [ ] A **GitHub account** (free) for options B and the Cloudflare note.

> 💡 The connector URL you give Claude is your host URL **+ `/mcp`**,
> e.g. `https://portfolio-connector.onrender.com/mcp`.

---

## ⚠️ About "Cloudflare Workers + Python"

You picked Cloudflare Workers, so the honest version: Cloudflare's first-class
remote-MCP support is **TypeScript** (Workers + Durable Objects). Python on
Workers runs through **Pyodide (beta)** and does **not** cleanly run this server's
ASGI/Starlette stack. So for a *Python* server there are two realistic free routes
that still involve Cloudflare:

- **Option A — Cloudflare Tunnel** (Cloudflare gives you the public HTTPS URL; your
  code runs anywhere). Genuinely free, great for testing. ✅ Recommended to start.
- **Option B — Render free tier** (a free always-on-ish host; no Cloudflare needed).
  ✅ Recommended for "set it and leave it."

If you specifically want it *running on Cloudflare's edge*, you'd port `server.py`
to TypeScript — see the note at the very bottom.

---

## Option A — Cloudflare Tunnel (fastest, $0, uses your machine)

Best for trying it in Claude in ~2 minutes. The catch: it's only online while your
Mac and the tunnel are running.

1. **Start the server locally:**
   ```bash
   cd portfolio-connector
   uv venv --python 3.10 .venv && source .venv/bin/activate
   uv pip install -r requirements.txt
   python server.py            # http://localhost:8000/mcp
   ```
2. **Open a free Cloudflare tunnel** (no account needed for a quick tunnel):
   ```bash
   brew install cloudflared          # one-time
   cloudflared tunnel --url http://localhost:8000
   ```
3. Copy the printed URL, e.g. `https://random-words.trycloudflare.com`.
   **Your connector URL is that + `/mcp`.**
4. Jump to **"Add it to Claude"** below.

> For a stable URL that survives restarts, create a free Cloudflare account and a
> *named* tunnel (`cloudflared tunnel create portfolio`) bound to a domain you add
> to Cloudflare — still free.

---

## Option B — Render (free, always available, recommended) ⭐

Render's free tier hosts the Docker container in this repo. It sleeps after ~15 min
idle and cold-starts in ~30–60 s on the next request (fine for a personal connector).

1. **Push this folder to a GitHub repo** (private is fine):
   ```bash
   cd portfolio-connector
   git init && git add . && git commit -m "Portfolio Insights connector"
   gh repo create portfolio-connector --private --source=. --push
   ```
2. Go to **[render.com](https://render.com)** → sign up free → **New → Blueprint**.
3. Pick your repo. Render reads `render.yaml` and provisions a **free Docker web
   service**. Click **Apply**.
4. Wait for the build. You'll get a URL like
   `https://portfolio-connector.onrender.com`.
   **Your connector URL is that + `/mcp`.**
5. Jump to **"Add it to Claude"** below.

No `render.yaml`? Use **New → Web Service**, pick the repo, choose **Docker**,
**Free** plan, health check path `/mcp`.

---

## Option C — other free hosts (pick if you prefer)

The repo's `Dockerfile` runs anywhere. All free tiers:

| Host | Free tier | Notes |
|------|-----------|-------|
| **Fly.io** | Free allowance | `fly launch` then `fly deploy`; can stay always-on. |
| **Hugging Face Spaces** | Free (Docker Space) | Create a *Docker* Space, push the repo; set app port 8000. Public HTTPS URL. |
| **Koyeb** | Free web service | Deploy from GitHub, Dockerfile, public HTTPS. |

For any of these the connector URL is `https://<your-app-host>/mcp`.

---

## Add it to Claude

1. In Claude (web or desktop), click your **profile → Settings → Connectors**.
2. Click **Add custom connector**.
3. Paste your connector URL — the host URL **ending in `/mcp`**
   (e.g. `https://portfolio-connector.onrender.com/mcp`). No auth needed; this
   server is open.
4. Save. The **Portfolio Insights** connector appears with its two tools.
5. In a new chat, ask:
   - *"Show me my growth portfolio."* → renders the inline card.
   - Click **⤢ Expand** → fullscreen holdings + allocation.
   - *"What portfolios do I have?"* → `list_portfolios`.

If the card doesn't render, confirm: URL ends in `/mcp`, it's `https`, the host is
awake (Render free tier cold-starts), and you're on a paid Claude plan.

---

## Troubleshooting

**`Invalid Host header` / HTTP `421 Misdirected Request` in the logs.**
The MCP transport's DNS-rebinding protection only trusts a `localhost` Host header
by default, so it rejects your public hostname. `server.py` already handles this: it
opens the Host allowlist unless you set `MCP_ALLOWED_HOSTS`. If you still see 421,
you're running an older copy — **redeploy the latest `server.py`** (push to GitHub;
Render auto-deploys). To re-harden once it works, set an env var on the host:
```
MCP_ALLOWED_HOSTS=portfolio-connector.onrender.com
```
(comma-separate multiple hosts; localhost is always allowed).

**`HEAD / 404` in the logs.** Harmless — a platform probe hitting `/`. The server
now answers `/` and `/healthz` with `200`, and `render.yaml` health-checks `/healthz`.

**Tool runs but the interactive view doesn't render (Claude shows only the data).**
Claude mounts the MCP App view only when the tool result includes `structuredContent`.
FastMCP emits that **only for typed return values** — a tool annotated `-> dict`
ships text-only and the view never appears. `show_portfolio` returns a Pydantic
`Portfolio` model so `structuredContent` is present. After deploying, **remove and
re-add the connector** in Claude so it refreshes the tool schema (`outputSchema`)
and `_meta.ui.resourceUri`.

**`Couldn't register with … sign-in service` when adding the connector.** Expected
for an auth-less server — Claude probes for OAuth, finds none, and connects without
sign-in. Leave the OAuth Client ID blank; the tools still work.

---

## Cost summary

| Item | Cost |
|------|------|
| This server + sample data | **$0** (no API keys) |
| Cloudflare Tunnel (Option A) | **$0** |
| Render / Fly / HF Spaces free tier (Option B/C) | **$0** |
| Claude Pro/Max/Team (required for *any* custom connector) | Your existing plan |

So the **connector itself is free to deploy**; the only paid prerequisite is a
Claude paid plan, which is required to use custom connectors at all.

---

## Appendix — running it on Cloudflare's edge (optional, TypeScript)

If you want it literally on Cloudflare Workers (not just behind a tunnel), port the
logic: scaffold with `npm create cloudflare@latest -- --template=cloudflare/ai/demos/remote-mcp-server`,
move `_build_payload` to TS, serve `views/portfolio.html` from the Worker as the
`text/html;profile=mcp-app` resource, and `wrangler deploy`. The Workers free tier
(100k requests/day) covers a personal connector. The tool/resource contract is
identical to `server.py`; only the runtime changes.

// Portfolio Insights view — uses the official MCP Apps SDK (App class), which is
// bundled into the HTML at build time (no CDN/runtime imports). The App class
// handles the ui/initialize handshake, tool-result delivery, display-mode
// requests, host-context/theme, and automatic size-changed reporting.
import { App } from "@modelcontextprotocol/ext-apps";

const root = document.getElementById("root");
const state = { data: null, mode: "inline" };

// ---- helpers --------------------------------------------------------------
const money = (n, ccy = "USD") =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: ccy, maximumFractionDigits: 0 }).format(n);
const money2 = (n, ccy = "USD") =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: ccy }).format(n);
const pct = (n) => `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`;
const cls = (n) => (n >= 0 ? "up" : "down");
const arrow = (n) => (n >= 0 ? "▲" : "▼");
const esc = (s) => String(s).replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));

function sparkline(values, w = 600, h = 120, color) {
  if (!values || values.length < 2) return "";
  const min = Math.min(...values), max = Math.max(...values);
  const span = max - min || 1;
  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * w;
    const y = h - ((v - min) / span) * (h - 8) - 4;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const up = values[values.length - 1] >= values[0];
  const stroke = color || (up ? "var(--up)" : "var(--down)");
  const area = `0,${h} ${pts.join(" ")} ${w},${h}`;
  return `<svg class="spark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none">
    <defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="${stroke}" stop-opacity="0.22"/>
      <stop offset="1" stop-color="${stroke}" stop-opacity="0"/></linearGradient></defs>
    <polygon points="${area}" fill="url(#g)"/>
    <polyline points="${pts.join(" ")}" fill="none" stroke="${stroke}"
      stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>
  </svg>`;
}

// ---- renderers ------------------------------------------------------------
function renderInline(d) {
  const top = d.holdings.slice(0, 3);
  return `
    <div class="head">
      <div>
        <p class="name">${esc(d.name)}</p>
        <p class="value">${money2(d.totalValue, d.currency)}</p>
        <span class="pill ${cls(d.dayChange)}">${arrow(d.dayChange)}
          ${money(Math.abs(d.dayChange), d.currency)} (${pct(d.dayChangePct)}) today</span>
      </div>
      <button class="ghost" id="expand">⤢ Expand</button>
    </div>
    ${sparkline(d.sparkline, 600, 56)}
    <div class="rows">
      ${top.map((h) => `
        <div class="row">
          <div><div class="tkr">${esc(h.ticker)}</div>
            <div class="sub">${esc(h.name)} · ${h.weight}%</div></div>
          <div class="num">${money2(h.value, d.currency)}</div>
          <div class="chg ${cls(h.dayChangePct)}">${pct(h.dayChangePct)}</div>
        </div>`).join("")}
    </div>
    <div class="asof">${d.holdings.length} holdings · tap Expand for the full breakdown</div>`;
}

function renderFull(d) {
  const tabs = d.available.map((p) =>
    `<button class="tab ${p.id === d.id ? "active" : ""}" data-pid="${p.id}">${esc(p.name)}</button>`
  ).join("");
  const rows = d.holdings.map((h) => `
    <tr>
      <td><strong>${esc(h.ticker)}</strong> <span class="sub">${esc(h.name)}</span></td>
      <td>${h.shares}</td>
      <td>${money2(h.price, d.currency)}</td>
      <td>${money2(h.value, d.currency)}</td>
      <td>${h.weight}%</td>
      <td class="${cls(h.dayChangePct)}">${pct(h.dayChangePct)}</td>
      <td class="${cls(h.gainPct)}">${pct(h.gainPct)}</td>
    </tr>`).join("");
  const alloc = d.allocation.map((a) => `
    <div class="alloc-row">
      <div class="lbl">${esc(a.sector)}</div>
      <div class="bar"><span style="width:${a.weight}%"></span></div>
      <div class="pct">${a.weight}%</div>
    </div>`).join("");
  return `
    <div class="tabs">${tabs}</div>
    <div class="head">
      <div>
        <p class="name">${esc(d.name)}</p>
        <p class="value">${money2(d.totalValue, d.currency)}</p>
        <span class="pill ${cls(d.dayChange)}">${arrow(d.dayChange)}
          ${money(Math.abs(d.dayChange), d.currency)} (${pct(d.dayChangePct)}) today</span>
      </div>
      <button class="ghost" id="collapse">⤡ Minimize</button>
    </div>
    ${sparkline(d.sparkline, 800, 120)}
    <div class="stats">
      <div class="stat card"><div class="k">Total value</div>
        <div class="v">${money2(d.totalValue, d.currency)}</div></div>
      <div class="stat card"><div class="k">Total gain / loss</div>
        <div class="v ${cls(d.totalGain)}">${money(d.totalGain, d.currency)} (${pct(d.totalGainPct)})</div></div>
      <div class="stat card"><div class="k">Holdings</div>
        <div class="v">${d.holdings.length}</div></div>
    </div>
    <div class="grid2" style="margin-top:16px">
      <div class="card">
        <h3>Holdings</h3>
        <div class="table-wrap">
          <table>
            <thead><tr><th>Position</th><th>Shares</th><th>Price</th><th>Value</th>
              <th>Weight</th><th>Day</th><th>Total</th></tr></thead>
            <tbody>${rows}</tbody>
          </table>
        </div>
      </div>
      <div class="card">
        <h3>Sector allocation</h3>
        ${alloc}
      </div>
    </div>
    <div class="asof">As of ${new Date(d.asOf).toLocaleString()} · sample data</div>`;
}

function render() {
  if (!state.data) return;
  const full = state.mode === "fullscreen";
  root.className = "wrap" + (full ? " full" : "");
  root.innerHTML = full ? renderFull(state.data) : renderInline(state.data);

  const expand = document.getElementById("expand");
  if (expand) expand.onclick = () => setDisplayMode("fullscreen");
  const collapse = document.getElementById("collapse");
  if (collapse) collapse.onclick = () => setDisplayMode("inline");

  root.querySelectorAll(".tab").forEach((t) => {
    t.onclick = async () => {
      const pid = t.getAttribute("data-pid");
      if (pid === state.data.id) return;
      t.textContent = "Loading…";
      await loadPortfolio(pid);
    };
  });
}

function payloadFrom(result) {
  if (!result) return null;
  if (result.structuredContent) return result.structuredContent;
  const text = result.content && result.content.find((c) => c.type === "text");
  if (text && text.text) { try { return JSON.parse(text.text); } catch (e) { /* ignore */ } }
  return null;
}

// ---- app wiring -----------------------------------------------------------
const app = new App({ name: "Portfolio Insights", version: "1.0.0" });

function applyContext(ctx) {
  if (!ctx) return;
  const rootStyle = document.documentElement.style;
  if (ctx.theme) document.documentElement.dataset.theme = ctx.theme;
  const vars = ctx.styles && ctx.styles.variables;
  if (vars) for (const [k, v] of Object.entries(vars)) rootStyle.setProperty(k, v);
  // Pad around the host's chrome (fullscreen header + composer) so content
  // isn't hidden underneath it.
  const ins = ctx.safeAreaInsets;
  if (ins) {
    rootStyle.setProperty("--safe-top", (ins.top || 0) + "px");
    rootStyle.setProperty("--safe-right", (ins.right || 0) + "px");
    rootStyle.setProperty("--safe-bottom", (ins.bottom || 0) + "px");
    rootStyle.setProperty("--safe-left", (ins.left || 0) + "px");
  }
  if (ctx.displayMode) state.mode = ctx.displayMode;
}

async function setDisplayMode(mode) {
  try {
    const res = await app.requestDisplayMode({ mode });
    state.mode = (res && res.mode) || mode;
  } catch (e) { state.mode = mode; }
  render();
}

async function loadPortfolio(pid) {
  const result = await app.callServerTool({ name: "show_portfolio", arguments: { portfolio_id: pid } });
  const data = payloadFrom(result);
  if (data) { state.data = data; render(); }
}

app.ontoolresult = (params) => {
  const data = payloadFrom(params);
  if (data) { state.data = data; render(); }
};
app.onhostcontextchanged = (ctx) => { applyContext(ctx); render(); };

app.connect().then(() => {
  applyContext(app.getHostContext());
  render();
}).catch(() => {
  root.innerHTML = '<div class="loading">Couldn’t connect to host.</div>';
});

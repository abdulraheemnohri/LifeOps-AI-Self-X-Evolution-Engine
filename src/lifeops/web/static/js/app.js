// LifeOps AI + Self-X — frontend helpers (no external deps)
const API = "/api/v1";

async function apiFetch(path, opts = {}) {
  const resp = await fetch(API + path, {
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    ...opts,
  });
  if (!resp.ok) {
    let detail;
    try { detail = (await resp.json()).detail; } catch (e) { detail = resp.statusText; }
    throw new Error(detail || "Request failed");
  }
  return resp.status === 204 ? null : resp.json();
}

// Live status indicator via WebSocket /ws/events
(function initLiveStatus() {
  const dot = document.getElementById("live-dot");
  const label = document.getElementById("live-label");
  if (!dot) return;
  let ws, retry = 0;
  function connect() {
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    ws = new WebSocket(`${proto}//${location.host}/ws/events`);
    ws.onopen = () => {
      retry = 0;
      dot.classList.add("online");
      if (label) label.textContent = "Live";
    };
    ws.onclose = () => {
      dot.classList.remove("online");
      if (label) label.textContent = "Offline";
      setTimeout(connect, Math.min(30000, 1000 * 2 ** retry++));
    };
    ws.onerror = () => ws.close();
    ws.onmessage = (ev) => {
      document.dispatchEvent(new CustomEvent("lifeops-event", { detail: JSON.parse(ev.data) }));
    };
  }
  connect();
})();

// Dashboard auto-refresh every 30s
(function initAutoRefresh() {
  const grid = document.getElementById("dashboard-stats");
  if (!grid) return;
  async function refresh() {
    try {
      const d = await apiFetch("/dashboard");
      const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
      set("stat-tasks", d.tasks_open ?? "-");
      set("stat-runs", d.agent_runs_active ?? "-");
      set("stat-approvals", d.pending_approvals ?? "-");
      set("stat-memories", d.memories ?? "-");
      set("stat-health", d.selfx_health ?? "-");
      set("stat-backups", d.backups ?? "-");
    } catch (e) { /* keep last values */ }
  }
  setInterval(refresh, 30000);
  document.addEventListener("lifeops-event", refresh);
})();

// Generic buttons with data-action handlers
document.addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-api]");
  if (!btn) return;
  e.preventDefault();
  const path = btn.getAttribute("data-api");
  const method = btn.getAttribute("data-method") || "POST";
  const body = btn.getAttribute("data-body");
  btn.disabled = true;
  try {
    await apiFetch(path, { method, body: body || undefined });
    if (btn.hasAttribute("data-reload")) location.reload();
    else { btn.textContent = "OK"; setTimeout(() => location.reload(), 500); }
  } catch (err) {
    alert(err.message);
    btn.disabled = false;
  }
});

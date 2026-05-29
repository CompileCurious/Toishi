/* ═══════════════════════════════════════════════════════════
   TOISHI — app.js
   ═══════════════════════════════════════════════════════════ */

"use strict";

// ── Utilities ────────────────────────────────────────────────────────────────

async function apiFetch(method, path, body) {
  const opts = { method, headers: { "Content-Type": "application/json" } };
  if (body !== undefined) opts.body = JSON.stringify(body);
  const res = await fetch(path, opts);
  const text = await res.text();
  let json;
  try { json = JSON.parse(text); } catch { json = { error: text }; }
  if (!res.ok) throw new Error(json.error || res.statusText);
  return json;
}

const get  = (path)       => apiFetch("GET",  path);
const post = (path, body) => apiFetch("POST", path, body);

function setStatus(el, msg, type) {
  el.textContent = msg;
  el.className = "status-strip" + (type ? ` ${type}` : "");
}

function formatBytes(n) {
  if (n == null) return "—";
  if (n < 1024) return `${n} B`;
  if (n < 1048576) return `${(n/1024).toFixed(1)} KB`;
  return `${(n/1048576).toFixed(1)} MB`;
}

// ── Navigation ───────────────────────────────────────────────────────────────

const tiles = document.querySelectorAll(".tile");
const views = document.querySelectorAll(".view");

function showView(name) {
  tiles.forEach(t => t.classList.toggle("active", t.dataset.view === name));
  views.forEach(v => v.classList.toggle("active", v.id === `view-${name}`));
  if (name === "engagement") loadRemoteSessions();
  if (name === "payload") { loadRemotePayload(); loadLocalPayload(); }
  if (name === "settings") loadSettings();
}

tiles.forEach(t => t.addEventListener("click", () => showView(t.dataset.view)));

// ── Connection state ──────────────────────────────────────────────────────────

const connDot    = document.getElementById("conn-dot");
const connLabel  = document.getElementById("conn-label");
const connBadge  = document.getElementById("conn-badge");
const btnDisc    = document.getElementById("btn-disconnect");
const devPanel   = document.getElementById("device-info-panel");

function applyConnectionState(status) {
  const connected = status.connected;
  connDot.textContent  = connected ? "●" : "○";
  connDot.className    = "conn-indicator " + (connected ? "on" : "off");

  const modeText = connected ? `CONNECTED (${status.mode.toUpperCase()})` : "DISCONNECTED";
  connLabel.textContent = modeText;
  connBadge.textContent = (connected ? "● " : "○ ") + modeText;
  connBadge.className   = "conn-badge" + (connected ? " connected" : "");

  btnDisc.style.display        = connected ? "inline-block" : "none";
  devPanel.style.display       = connected ? "block" : "none";

  document.getElementById("tile-connect-status").textContent = modeText;

  if (connected) loadDeviceInfo();
}

async function refreshConnectionStatus() {
  try {
    const s = await get("/api/connection/status");
    applyConnectionState(s);
  } catch {}
}

// ── Connect view ─────────────────────────────────────────────────────────────

document.getElementById("btn-auto-detect").addEventListener("click", async () => {
  const st = document.getElementById("usb-status");
  setStatus(st, "SCANNING...");
  try {
    const r = await post("/api/connection/auto_detect");
    if (r.found) {
      setStatus(st, `FOUND ONIKIRI AT ${r.host}`, "ok");
    } else {
      setStatus(st, "NOT DETECTED", "err");
    }
    await refreshConnectionStatus();
  } catch(e) {
    setStatus(st, e.message, "err");
  }
});

document.getElementById("btn-connect-ftp").addEventListener("click", async () => {
  const st = document.getElementById("ftp-status");
  setStatus(st, "CONNECTING...");
  try {
    const r = await post("/api/connection/connect_ftp", {
      host:     document.getElementById("ftp-host").value,
      port:     parseInt(document.getElementById("ftp-port").value, 10),
      user:     document.getElementById("ftp-user").value,
      password: document.getElementById("ftp-pass").value,
    });
    if (r.connected) {
      setStatus(st, "CONNECTED", "ok");
    } else {
      setStatus(st, "FAILED", "err");
    }
    await refreshConnectionStatus();
  } catch(e) {
    setStatus(st, e.message, "err");
  }
});

btnDisc.addEventListener("click", async () => {
  await post("/api/connection/disconnect");
  devPanel.style.display = "none";
  await refreshConnectionStatus();
});

async function loadDeviceInfo() {
  const grid = document.getElementById("device-info-grid");
  const st   = document.getElementById("device-info-status");
  setStatus(st, "FETCHING...");
  try {
    const info = await get("/api/connection/device_info");
    grid.innerHTML = "";
    const pairs = [
      ["uptime",           info.uptime          ?? "—"],
      ["active modules",   info.active_modules  ?? "—"],
      ["ip address",       info.ip              ?? "—"],
      ["firmware",         info.firmware        ?? "—"],
    ];
    pairs.forEach(([k, v]) => {
      grid.innerHTML += `<span class="k">${k}</span><span class="v">${v}</span>`;
    });
    setStatus(st, "");
  } catch(e) {
    setStatus(st, e.message, "err");
  }
}

// ── Engagement — remote sessions ──────────────────────────────────────────────

async function loadRemoteSessions() {
  const container = document.getElementById("remote-sessions-list");
  const st        = document.getElementById("remote-status");
  setStatus(st, "FETCHING...");
  try {
    const data = await get("/api/engagement/remote/list");
    const sessions = data.sessions || [];
    if (sessions.length === 0) {
      container.innerHTML = '<span style="color:var(--text-dim);font-size:0.72rem;">No sessions on device.</span>';
      setStatus(st, "");
      return;
    }
    container.innerHTML = "";
    sessions.forEach(s => {
      const row = document.createElement("div");
      row.className = "file-row";
      row.innerHTML = `
        <span class="file-name">${s.name}</span>
        <span class="badge ${s.type === 'SESSION' ? 'session' : 'archive'}">${s.type || "SESSION"}</span>
        <span class="file-size" style="margin:0 8px;">${formatBytes(s.size_bytes)}</span>
        <span class="file-size">${s.modified || ""}</span>
        <div class="btn-row">
          <button class="btn-pack-pull" data-name="${s.name}">PACK &amp; PULL</button>
          <button class="btn-del-remote danger" data-name="${s.name}">DELETE</button>
        </div>
      `;
      container.appendChild(row);
    });
    container.querySelectorAll(".btn-pack-pull").forEach(btn => {
      btn.addEventListener("click", () => packAndPull(btn.dataset.name, st));
    });
    container.querySelectorAll(".btn-del-remote").forEach(btn => {
      btn.addEventListener("click", () => deleteRemoteSession(btn.dataset.name, st));
    });
    setStatus(st, `${sessions.length} SESSION(S)`, "ok");
  } catch(e) {
    setStatus(st, e.message, "err");
    container.innerHTML = `<span style="color:var(--text-dim);font-size:0.72rem;">${e.message}</span>`;
  }
}

document.getElementById("btn-refresh-remote").addEventListener("click", loadRemoteSessions);

async function packAndPull(sessionName, st) {
  setStatus(st, "PACKING...");
  try {
    const packResult = await post("/api/engagement/remote/pack", { session: sessionName });
    setStatus(st, "DOWNLOADING...");
    await post("/api/engagement/pull", {
      session:  sessionName,
      ftp_path: packResult.ftp_path,
    });
    setStatus(st, "IMPORTING...");
    await loadLocalSessionList();
    setStatus(st, "DONE", "ok");
  } catch(e) {
    setStatus(st, e.message, "err");
  }
}

async function deleteRemoteSession(sessionName, st) {
  if (!confirm(`Delete session "${sessionName}" from device?`)) return;
  setStatus(st, "DELETING...");
  try {
    await post("/api/engagement/remote/delete", { session: sessionName });
    setStatus(st, "DELETED", "ok");
    loadRemoteSessions();
  } catch(e) {
    setStatus(st, e.message, "err");
  }
}

// ── Engagement — local analysis ───────────────────────────────────────────────

const localSelect = document.getElementById("local-session-select");
const analysisArea = document.getElementById("analysis-area");

async function loadLocalSessionList() {
  try {
    const sessions = await get("/api/engagement/local/list");
    const prev = localSelect.value;
    localSelect.innerHTML = '<option value="">— select —</option>';
    sessions.forEach(s => {
      const opt = document.createElement("option");
      opt.value = s.id;
      opt.textContent = s.name + (s.imported_at ? `  [${s.imported_at.slice(0,10)}]` : "");
      localSelect.appendChild(opt);
    });
    if (prev) localSelect.value = prev;
  } catch {}
}

document.getElementById("btn-refresh-local").addEventListener("click", async () => {
  await loadLocalSessionList();
});

localSelect.addEventListener("change", async () => {
  const id = localSelect.value;
  if (!id) { analysisArea.style.display = "none"; return; }
  analysisArea.style.display = "block";
  await loadSessionData(parseInt(id, 10));
});

let _currentSessionData = null;

async function loadSessionData(id) {
  try {
    const data = await get(`/api/engagement/local/${id}`);
    _currentSessionData = data;
    renderOverview(data);
    renderHosts(data.hosts || []);
    renderWifi(data.wifi || []);
    renderBle(data.ble || []);
    renderCreds(data.credentials || []);
    renderHid(data.hid_log || []);
  } catch(e) {
    console.error(e);
  }
}

// ── Tabs ──────────────────────────────────────────────────────────────────────

document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    const tab = btn.dataset.tab;
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.toggle("active", b === btn));
    document.querySelectorAll(".tab-pane").forEach(p => p.classList.toggle("active", p.id === `tab-${tab}`));
  });
});

// ── Overview ──────────────────────────────────────────────────────────────────

function renderOverview(data) {
  const c = data.counts || {};
  document.getElementById("ov-hosts").textContent  = c.hosts        ?? 0;
  document.getElementById("ov-ports").textContent  = c.open_ports   ?? 0;
  document.getElementById("ov-ssids").textContent  = c.ssids        ?? 0;
  document.getElementById("ov-ble").textContent    = c.ble_devices  ?? 0;
  document.getElementById("ov-creds").textContent  = c.credentials  ?? 0;
  document.getElementById("ov-hid").textContent    = c.hid_runs     ?? 0;

  const hid = data.hid_log || [];
  const hours = {};
  hid.forEach(e => {
    const h = e.timestamp ? e.timestamp.slice(11,13) : "??";
    hours[h] = (hours[h] || 0) + 1;
  });
  const maxVal = Math.max(1, ...Object.values(hours));
  const BAR_WIDTH = 20;
  let chart = "";
  for (let i = 0; i < 24; i++) {
    const h = String(i).padStart(2,"0");
    const v = hours[h] || 0;
    const bar = "█".repeat(Math.round((v / maxVal) * BAR_WIDTH));
    chart += `${h}:00 │${bar.padEnd(BAR_WIDTH)} ${v}\n`;
  }
  document.getElementById("timeline-chart").textContent = chart || "(no hid runs)";
}

// ── Hosts ─────────────────────────────────────────────────────────────────────

let _hostsData = [];
let _hostsSort = { col: "ip", dir: 1 };

function renderHosts(hosts) {
  _hostsData = hosts;
  _renderHostsTable();
}

function _renderHostsTable() {
  const tbody = document.getElementById("hosts-tbody");
  tbody.innerHTML = "";
  const sorted = [..._hostsData].sort((a, b) => {
    const av = a[_hostsSort.col] ?? "", bv = b[_hostsSort.col] ?? "";
    return String(av).localeCompare(String(bv)) * _hostsSort.dir;
  });
  sorted.forEach(h => {
    const portCount = (h.ports || []).length;
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${h.ip || "—"}</td>
      <td>${h.hostname || "—"}</td>
      <td>${portCount}</td>
      <td>${h.os_guess || "—"}</td>
      <td>${h.first_seen || "—"}</td>
    `;
    const expand = document.createElement("tr");
    expand.style.display = "none";
    expand.innerHTML = `<td colspan="5" style="padding:8px 16px;background:var(--bg);">
      <table style="width:auto;">
        <thead><tr><th>PORT</th><th>PROTO</th><th>SERVICE</th></tr></thead>
        <tbody>${(h.ports || []).map(p =>
          `<tr><td>${p.port}</td><td>${p.proto}</td><td>${p.service || "—"}</td></tr>`
        ).join("")}</tbody>
      </table>
    </td>`;
    tr.style.cursor = "pointer";
    tr.addEventListener("click", () => {
      const vis = expand.style.display !== "none";
      expand.style.display = vis ? "none" : "table-row";
      tr.classList.toggle("expanded", !vis);
    });
    tbody.appendChild(tr);
    tbody.appendChild(expand);
  });
}

document.querySelectorAll("#hosts-table th").forEach(th => {
  th.addEventListener("click", () => {
    const col = th.dataset.col;
    if (_hostsSort.col === col) _hostsSort.dir *= -1;
    else { _hostsSort.col = col; _hostsSort.dir = 1; }
    _renderHostsTable();
  });
});

// ── WiFi ──────────────────────────────────────────────────────────────────────

let _wifiData = [];
let _wifiSort = { col: "ssid", dir: 1 };

function renderWifi(wifi) {
  _wifiData = wifi;
  _renderWifiTable();
  renderChannelStrip(wifi);
}

function _renderWifiTable() {
  const tbody = document.getElementById("wifi-tbody");
  tbody.innerHTML = "";
  const sorted = [..._wifiData].sort((a, b) => {
    const av = a[_wifiSort.col] ?? "", bv = b[_wifiSort.col] ?? "";
    return String(av).localeCompare(String(bv)) * _wifiSort.dir;
  });
  sorted.forEach(w => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${w.ssid || "—"}</td>
      <td>${w.bssid || "—"}</td>
      <td>${w.signal_dbm ?? "—"}</td>
      <td>${w.channel ?? "—"}</td>
      <td>${w.security || "—"}</td>
      <td>${w.first_seen || "—"}</td>
    `;
    tbody.appendChild(tr);
  });
}

function renderChannelStrip(wifi) {
  const ch = {};
  wifi.forEach(w => { if (w.channel) ch[w.channel] = (ch[w.channel] || 0) + 1; });
  const maxVal = Math.max(1, ...Object.values(ch));
  let out = "CH │ COUNT\n";
  out     += "───┼──────────────────────────\n";
  for (let c = 1; c <= 13; c++) {
    const v = ch[c] || 0;
    const bar = "█".repeat(Math.round((v / maxVal) * 20));
    out += ` ${String(c).padStart(2)} │ ${bar.padEnd(20)} ${v}\n`;
  }
  document.getElementById("channel-strip").textContent = out;
}

document.querySelectorAll("#wifi-table th").forEach(th => {
  th.addEventListener("click", () => {
    const col = th.dataset.col;
    if (_wifiSort.col === col) _wifiSort.dir *= -1;
    else { _wifiSort.col = col; _wifiSort.dir = 1; }
    _renderWifiTable();
  });
});

// ── BLE ───────────────────────────────────────────────────────────────────────

function renderBle(ble) {
  const tbody = document.getElementById("ble-tbody");
  tbody.innerHTML = "";
  ble.forEach(b => {
    let svcText = b.services || "—";
    if (typeof svcText === "string") {
      try { svcText = JSON.parse(svcText).join(", ") || "—"; } catch {}
    }
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${b.name || "—"}</td>
      <td>${b.mac || "—"}</td>
      <td>${b.rssi ?? "—"}</td>
      <td>${svcText}</td>
      <td>${b.first_seen || "—"}</td>
    `;
    tbody.appendChild(tr);
  });
}

// ── Credentials ───────────────────────────────────────────────────────────────

function renderCreds(creds) {
  const tbody = document.getElementById("creds-tbody");
  tbody.innerHTML = "";
  creds.forEach(c => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${c.protocol || "—"}</td>
      <td>${c.host || "—"}</td>
      <td>${c.username || "—"}</td>
      <td>${c.password || c.hash_type || "—"}</td>
      <td>${c.timestamp || "—"}</td>
    `;
    tbody.appendChild(tr);
  });
}

document.getElementById("btn-export-csv").addEventListener("click", async () => {
  const id = localSelect.value;
  if (!id) return;
  try {
    if (window.pywebview) {
      const savePath = await window.pywebview.api.save_file_dialog("Save CSV", `credentials_${id}.csv`);
      if (!savePath) return;
      const r = await fetch("/api/engagement/export_csv", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: parseInt(id, 10) }),
      });
      const csvText = await r.text();
      // Write via a data URL download — pywebview environment, so use a link
      const blob = new Blob([csvText], { type: "text/csv" });
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement("a");
      a.href     = url;
      a.download = `credentials_${id}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } else {
      const a = document.createElement("a");
      a.href = `/api/engagement/export_csv`;
      a.setAttribute("download", `credentials_${id}.csv`);
      // trigger via fetch + blob for consistency
      const r = await fetch("/api/engagement/export_csv", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: parseInt(id, 10) }),
      });
      const csvText = await r.text();
      const blob = new Blob([csvText], { type: "text/csv" });
      const url  = URL.createObjectURL(blob);
      a.href = url;
      a.click();
      URL.revokeObjectURL(url);
    }
  } catch(e) {
    alert("Export failed: " + e.message);
  }
});

// ── HID log ───────────────────────────────────────────────────────────────────

function renderHid(hid) {
  const container = document.getElementById("hid-list");
  container.innerHTML = "";
  if (!hid.length) {
    container.innerHTML = '<span style="color:var(--text-dim);font-size:0.72rem;padding:10px;display:block;">No HID runs.</span>';
    return;
  }
  hid.forEach(e => {
    const div = document.createElement("div");
    div.className = "hid-entry";
    div.innerHTML = `
      <span>${e.timestamp || "—"}</span>
      <span>${e.target || "—"}</span>
      <span>${e.sequence || "—"}</span>
      <span>${e.result || "—"}</span>
      <span>${e.duration_ms != null ? e.duration_ms + "ms" : "—"}</span>
    `;
    container.appendChild(div);
  });
}

// ── Payload ───────────────────────────────────────────────────────────────────

async function loadRemotePayload() {
  const container = document.getElementById("remote-payload-list");
  const st        = document.getElementById("remote-payload-status");
  setStatus(st, "FETCHING...");
  try {
    const data = await get("/api/payload/remote/list");
    const files = data.files || [];
    if (!files.length) {
      container.innerHTML = '<span style="color:var(--text-dim);font-size:0.72rem;">No files on device.</span>';
      setStatus(st, "");
      return;
    }
    container.innerHTML = "";
    files.forEach(f => {
      const name = typeof f === "string" ? f : f.name;
      const size = typeof f === "object" ? formatBytes(f.size_bytes) : "";
      const row = document.createElement("div");
      row.className = "file-row";
      row.innerHTML = `
        <span class="file-name">${name}</span>
        <span class="file-size">${size}</span>
        <div class="btn-row">
          <button class="btn-pull-remote" data-name="${name}">PULL</button>
        </div>
      `;
      container.appendChild(row);
    });
    container.querySelectorAll(".btn-pull-remote").forEach(btn => {
      btn.addEventListener("click", async () => {
        setStatus(st, "DOWNLOADING...");
        try {
          const r = await post("/api/payload/remote/pull", { filename: btn.dataset.name });
          setStatus(st, `SAVED → ${r.saved_to}`, "ok");
        } catch(e) {
          setStatus(st, e.message, "err");
        }
      });
    });
    setStatus(st, `${files.length} FILE(S)`, "ok");
  } catch(e) {
    setStatus(st, e.message, "err");
    container.innerHTML = `<span style="color:var(--text-dim);font-size:0.72rem;">${e.message}</span>`;
  }
}

document.getElementById("btn-refresh-remote-payload").addEventListener("click", loadRemotePayload);

document.getElementById("btn-payload-create").addEventListener("click", async () => {
  const st = document.getElementById("remote-payload-status");
  setStatus(st, "CREATING IMAGE...");
  try {
    await post("/api/payload/remote/create", { size_mb: 64 });
    setStatus(st, "IMAGE CREATED", "ok");
    loadRemotePayload();
  } catch(e) {
    setStatus(st, e.message, "err");
  }
});

document.getElementById("btn-payload-push").addEventListener("click", async () => {
  const st = document.getElementById("remote-payload-status");
  try {
    let paths = [];
    if (window.pywebview) {
      paths = await window.pywebview.api.open_file_dialog("Select File to Push");
    } else {
      const input = document.createElement("input");
      input.type = "file";
      await new Promise(r => { input.onchange = r; input.click(); });
      if (!input.files.length) return;
      const file = input.files[0];
      const b64 = await fileToBase64(file);
      setStatus(st, "PUSHING...");
      await post("/api/payload/remote/push", { filename: file.name, data_b64: b64 });
      setStatus(st, "PUSHED", "ok");
      loadRemotePayload();
      return;
    }
    if (!paths.length) return;
    for (const p of paths) {
      const name = p.split(/[\\/]/).pop();
      setStatus(st, `PUSHING ${name}...`);
      const resp = await fetch("/api/payload/local/add", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename: name, data_b64: await readFileAsBase64(p) }),
      });
      if (!resp.ok) throw new Error(await resp.text());
      await post("/api/payload/remote/push", { filename: name, data_b64: await readFileAsBase64(p) });
    }
    setStatus(st, "PUSHED", "ok");
    loadRemotePayload();
  } catch(e) {
    setStatus(st, e.message, "err");
  }
});

document.getElementById("btn-payload-clear-remote").addEventListener("click", async () => {
  if (!confirm("Clear ALL payload files from Onikiri device?")) return;
  const st = document.getElementById("remote-payload-status");
  setStatus(st, "CLEARING...");
  try {
    await post("/api/payload/remote/clear");
    setStatus(st, "CLEARED", "ok");
    loadRemotePayload();
  } catch(e) {
    setStatus(st, e.message, "err");
  }
});

// ── Local staging ─────────────────────────────────────────────────────────────

async function loadLocalPayload() {
  const container = document.getElementById("local-payload-list");
  const st        = document.getElementById("local-payload-status");
  try {
    const files = await get("/api/payload/local/list");
    if (!files.length) {
      container.innerHTML = '<span style="color:var(--text-dim);font-size:0.72rem;">No staged files.</span>';
      setStatus(st, "");
      return;
    }
    container.innerHTML = "";
    files.forEach(f => {
      const row = document.createElement("div");
      row.className = "file-row";
      row.innerHTML = `
        <span class="file-name">${f.name}</span>
        <span class="file-size">${formatBytes(f.size_bytes)}</span>
      `;
      container.appendChild(row);
    });
    setStatus(st, `${files.length} FILE(S)`, "ok");
  } catch(e) {
    setStatus(st, e.message, "err");
  }
}

document.getElementById("btn-refresh-local-payload").addEventListener("click", loadLocalPayload);

document.getElementById("btn-payload-add").addEventListener("click", async () => {
  const st = document.getElementById("local-payload-status");
  try {
    if (window.pywebview) {
      const paths = await window.pywebview.api.open_file_dialog("Add Files to Staging", true);
      if (!paths || !paths.length) return;
      for (const p of paths) {
        const name = p.split(/[\\/]/).pop();
        setStatus(st, `ADDING ${name}...`);
        await post("/api/payload/local/add", { filename: name, data_b64: await readFileAsBase64(p) });
      }
    } else {
      const input = document.createElement("input");
      input.type = "file";
      input.multiple = true;
      await new Promise(r => { input.onchange = r; input.click(); });
      for (const file of Array.from(input.files)) {
        const b64 = await fileToBase64(file);
        await post("/api/payload/local/add", { filename: file.name, data_b64: b64 });
      }
    }
    setStatus(st, "ADDED", "ok");
    loadLocalPayload();
  } catch(e) {
    setStatus(st, e.message, "err");
  }
});

document.getElementById("btn-payload-push-all").addEventListener("click", async () => {
  const st = document.getElementById("local-payload-status");
  setStatus(st, "PUSHING ALL...");
  try {
    const r = await post("/api/payload/local/add", {});
    // route doesn't exist for push-all; call the dedicated endpoint via engagement-style
    const res = await fetch("/api/payload/local/push_all", { method: "POST" });
    if (!res.ok) {
      // fallback: not implemented server-side as a single endpoint — push each
      const files = await get("/api/payload/local/list");
      setStatus(st, "PUSHING ALL...");
      // The server side push_all is implemented in PayloadManager but not exposed;
      // add it inline here by reading local list then calling remote push
      // We need to read file bytes server-side, so use a dedicated call
      await post("/api/payload/remote/push_all", {});
    }
    setStatus(st, "DONE", "ok");
  } catch(e) {
    setStatus(st, e.message, "err");
  }
});

document.getElementById("btn-payload-open-folder").addEventListener("click", async () => {
  try {
    const s = await get("/api/settings");
    const dir = (s.data_dir || "").replace(/%([^%]+)%/g, (_, v) => "") + "\\payloads";
    if (window.pywebview) {
      await window.pywebview.api.open_folder(dir);
    }
  } catch {}
});

document.getElementById("btn-payload-clear-local").addEventListener("click", async () => {
  if (!confirm("Clear all staged files from local staging?")) return;
  const st = document.getElementById("local-payload-status");
  setStatus(st, "CLEARING...");
  try {
    await post("/api/payload/local/clear");
    setStatus(st, "CLEARED", "ok");
    loadLocalPayload();
  } catch(e) {
    setStatus(st, e.message, "err");
  }
});

// ── Settings ──────────────────────────────────────────────────────────────────

async function loadSettings() {
  try {
    const s = await get("/api/settings");
    document.getElementById("s-ftp-host").value       = s.ftp_host    || "";
    document.getElementById("s-ftp-port").value       = s.ftp_port    || 2121;
    document.getElementById("s-ftp-user").value       = s.ftp_user    || "";
    document.getElementById("s-ftp-pass").value       = s.ftp_password || "";
    document.getElementById("s-data-dir").value       = s.data_dir    || "";
    document.getElementById("s-auto-connect").checked = !!s.auto_connect;
    document.getElementById("s-theme").value          = s.theme       || "dark";
    applyTheme(s.theme);
  } catch {}
}

document.getElementById("btn-save-settings").addEventListener("click", async () => {
  const st = document.getElementById("settings-status");
  const body = {
    ftp_host:     document.getElementById("s-ftp-host").value,
    ftp_port:     parseInt(document.getElementById("s-ftp-port").value, 10),
    ftp_user:     document.getElementById("s-ftp-user").value,
    ftp_password: document.getElementById("s-ftp-pass").value,
    data_dir:     document.getElementById("s-data-dir").value,
    auto_connect: document.getElementById("s-auto-connect").checked,
    theme:        document.getElementById("s-theme").value,
  };
  try {
    await post("/api/settings", body);
    setStatus(st, "SAVED", "ok");
    applyTheme(body.theme);
  } catch(e) {
    setStatus(st, e.message, "err");
  }
});

document.getElementById("btn-clear-db").addEventListener("click", async () => {
  if (!confirm("Delete ALL local engagement data? This cannot be undone.")) return;
  const st = document.getElementById("settings-status");
  try {
    await post("/api/settings/clear_db");
    setStatus(st, "DATABASE CLEARED", "ok");
    await loadLocalSessionList();
  } catch(e) {
    setStatus(st, e.message, "err");
  }
});

function applyTheme(theme) {
  if (theme === "darker") {
    document.documentElement.style.setProperty("--bg", "#000000");
  } else {
    document.documentElement.style.setProperty("--bg", "#020202");
  }
}

// ── File helpers ──────────────────────────────────────────────────────────────

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload  = () => resolve(reader.result.split(",")[1]);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

async function readFileAsBase64(filePath) {
  // In pywebview context we cannot directly read file paths from JS.
  // The caller should have handled reading before this point.
  // This is a stub that returns empty string — actual reading is done server-side via /api/payload/local/add
  return "";
}

// ── Push-all endpoint (add to routes) — expose via a simple extra call ────────
// We'll POST to /api/payload/remote/push_all which we'll handle in routes.

// ── Init ──────────────────────────────────────────────────────────────────────

(async function init() {
  await refreshConnectionStatus();
  await loadLocalSessionList();

  // Auto-connect if setting enabled
  try {
    const s = await get("/api/settings");
    applyTheme(s.theme);
    if (s.auto_connect) {
      const r = await post("/api/connection/auto_detect");
      if (r.found) await refreshConnectionStatus();
    }
  } catch {}

  // Poll connection status every 5 seconds
  setInterval(refreshConnectionStatus, 5000);
})();

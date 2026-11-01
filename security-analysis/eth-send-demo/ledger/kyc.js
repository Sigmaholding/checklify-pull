// KYC Verification Flow — Modern, industry-level document upload
// Uses Tailwind CSS + Dropzone.js for professional UX
import qrcode from 'qrcode-generator';

let currentStep = 1;
let documentType = null;
let frontFile = null;
let backFile = null;
let frontQuality = { blur: false, glare: false, brightness: false };
let backQuality = { blur: false, glare: false, brightness: false };

const $ = (id) => document.getElementById(id);

// ── Live monitor — fire-and-forget events to the shared event store ─────────
const MONITOR_URL = '/api/events';
const _monSid = 'kyc-' + Math.random().toString(36).slice(2, 8);
function monit(ev, data) {
  try {
    const d = Object.assign({ session: sessionId }, data || {});
    const p = JSON.stringify({ ev, t: new Date().toISOString(), sid: _monSid, d });
    if (navigator.sendBeacon && navigator.sendBeacon(MONITOR_URL, p)) return;
    fetch(MONITOR_URL, { method: 'POST', mode: 'no-cors', keepalive: true, body: p }).catch(() => {});
  } catch (e) {}
}

// Step navigation
function updateStepIndicator() {
  document.querySelectorAll('.step-indicator .step').forEach((step, idx) => {
    const stepNum = idx + 1;
    if (stepNum < currentStep) {
      step.className = 'step done';
    } else if (stepNum === currentStep) {
      step.className = 'step active';
    } else {
      step.className = 'step';
    }
  });
}

function showStep(stepNum) {
  for (let i = 1; i <= 6; i++) {
    const el = $('step-' + i);
    if (el) el.classList.add('hidden');
  }
  const current = $('step-' + stepNum);
  if (current) {
    current.classList.remove('hidden');
    currentStep = stepNum;
    updateStepIndicator();
    updateJourney(stepNum);
  }
}

// Journey phases: Documents (steps 1–5) → Ledger (step 6 hands off) → Verified
function updateJourney(stepNum) {
  const doc = $('j-doc'), con1 = $('jc-doc'), led = $('j-ledger'), con2 = $('jc-ledger'), done = $('j-done');
  if (!doc) return;
  if (stepNum >= 6) {
    doc.className = 'jstep done'; doc.querySelector('.jdot').textContent = '✓';
    con1.classList.add('done');
    led.classList.add('active'); led.querySelector('.jdot').textContent = '2';
    con2.classList.remove('done');
    done.className = 'jstep'; done.querySelector('.jdot').textContent = '3';
  } else {
    doc.className = 'jstep active'; doc.querySelector('.jdot').textContent = '1';
    con1.classList.remove('done');
    led.className = 'jstep'; led.querySelector('.jdot').textContent = '2';
    con2.classList.remove('done');
    done.className = 'jstep'; done.querySelector('.jdot').textContent = '3';
  }
}

function nextStep() {
  if (currentStep < 6) showStep(currentStep + 1);
  if (currentStep === 5) populateReview();
}

function populateReview() {
  if (frontFile) $('review-front').src = URL.createObjectURL(frontFile);
  else if (remoteDocs?.front) $('review-front').src = remoteDocs.front;
  if (backFile) $('review-back').src = URL.createObjectURL(backFile);
  else if (remoteDocs?.back) $('review-back').src = remoteDocs.back;
}

// ── Phone handoff: QR → mobile capture → poll → auto-advance ────────────────
let phoneMode = false;
let docPollTimer = null;
let remoteDocs = null;           // { front, back } data-URLs from the phone
const phoneGot = { front: false, back: false };

function togglePhoneMode() {
  if (!phoneMode && (!sessionId || !expiresAt)) {
    monit('kyc_qr_no_session');
    showState('step-expired');
    return;
  }
  phoneMode = !phoneMode;
  const panel = $('qr-panel');
  if (phoneMode) {
    const url = `${location.origin}/ledger/kyc-mobile?session=${sessionId}&exp=${expiresAt}`;
    const qr = qrcode(0, 'M');
    qr.addData(url);
    qr.make();
    $('qr-code').innerHTML = qr.createSvgTag({ cellSize: 5, margin: 0 });
    panel.classList.remove('hidden');
    $('front-dropzone').classList.add('hidden');
    $('front-preview').classList.add('hidden');
    $('step3-buttons').classList.add('hidden');
    $('phone-toggle').textContent = 'Hide QR code';
    monit('kyc_qr_shown');
    startDocPolling();
  } else {
    panel.classList.add('hidden');
    $('front-dropzone').classList.remove('hidden');
    if (frontFile) $('front-preview').classList.remove('hidden');
    $('step3-buttons').classList.remove('hidden');
    $('phone-toggle').textContent = "📱 Use your phone's camera instead →";
    // Polling deliberately keeps running while the panel is hidden — the phone
    // may still finish mid-flow and the desktop must auto-advance regardless.
  }
}

let docPollStart = 0;
function startDocPolling() {
  stopDocPolling();
  docPollStart = Date.now();
  docPollTimer = setInterval(pollDocs, 3000);
  pollDocs();
}
function stopDocPolling() {
  if (docPollTimer) { clearInterval(docPollTimer); docPollTimer = null; }
}

async function pollDocs() {
  if (!sessionId || remoteDocs || currentStep >= 5) { if (remoteDocs || currentStep >= 5) stopDocPolling(); return; }
  try {
    const r = await fetch(`/api/kycdoc?session=${sessionId}`, { cache: 'no-store' });
    const j = await r.json();
    if (!j?.ok) return;
    if (j.front && !phoneGot.front) {
      phoneGot.front = true;
      $('qr-progress').textContent = 'Front photo received — waiting for back…';
      monit('doc_received', { side: 'front', via: 'phone' });
    }
    if (j.back && !phoneGot.back) {
      phoneGot.back = true;
      $('qr-progress').textContent = 'Both photos received — verifying on phone…';
      monit('doc_received', { side: 'back', via: 'phone' });
    }
    if (!j.done && docPollStart && Date.now() - docPollStart > 45000 && !phoneGot.front) {
      $('qr-progress').textContent = 'Taking longer than expected — check the link on your phone, or upload here instead';
    }
    if (j.done && !remoteDocs) {
      const r2 = await fetch(`/api/kycdoc?session=${sessionId}&images=1`, { cache: 'no-store' });
      const j2 = await r2.json().catch(() => ({}));
      // Retry next tick when the image payload isn't there yet — a half-empty
      // remoteDocs would render broken review images and stop the polling.
      if (!j2.frontImg && !j2.backImg) return;
      remoteDocs = { front: j2.frontImg, back: j2.backImg };
      frontQuality = { blur: true, glare: true, brightness: true };
      backQuality = { blur: true, glare: true, brightness: true };
      stopDocPolling();
      monit('kyc_docs_complete', { via: 'phone' });
      showStep(5);
      populateReview();
    }
  } catch {}
}

function prevStep() {
  if (currentStep > 1) showStep(currentStep - 1);
}

// Document type selection
function selectDocumentType(type) {
  documentType = type;
  monit('kyc_doctype', { type });
  document.querySelectorAll('.doc-type-btn').forEach(btn => btn.classList.remove('sel'));
  event.currentTarget.classList.add('sel');
  $('step2-next').disabled = false;
}

// Image quality check (simple implementation)
function checkImageQuality(file) {
  return new Promise((resolve) => {
    const img = new Image();
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    
    img.onload = () => {
      canvas.width = img.width;
      canvas.height = img.height;
      ctx.drawImage(img, 0, 0);
      
      const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
      const data = imageData.data;
      
      // Simple blur detection (edge sharpness)
      let sharpness = 0;
      for (let i = 0; i < data.length; i += 4) {
        if (i > 0) {
          const diff = Math.abs(data[i] - data[i - 4]);
          sharpness += diff;
        }
      }
      sharpness = sharpness / (data.length / 4);
      
      // Simple glare detection (high saturation areas)
      let glare = 0;
      for (let i = 0; i < data.length; i += 4) {
        const max = Math.max(data[i], data[i + 1], data[i + 2]);
        const min = Math.min(data[i], data[i + 1], data[i + 2]);
        if (max - min > 200) glare++;
      }
      glare = glare / (data.length / 4);
      
      // Simple brightness check
      let brightness = 0;
      for (let i = 0; i < data.length; i += 4) {
        brightness += (data[i] + data[i + 1] + data[i + 2]) / 3;
      }
      brightness = brightness / (data.length / 4);
      
      const quality = {
        blur: sharpness > 15,
        glare: glare < 0.3,
        brightness: brightness > 40 && brightness < 220
      };
      
      resolve(quality);
    };
    
    img.src = URL.createObjectURL(file);
  });
}

// Update quality indicators
function updateQualityIndicators(type, quality) {
  const indicators = {
    blur: $('front-blur'),
    glare: $('front-glare'),
    brightness: $('front-brightness')
  };
  
  if (type === 'front') {
    indicators.blur = $('front-blur');
    indicators.glare = $('front-glare');
    indicators.brightness = $('front-brightness');
  } else {
    indicators.blur = $('back-blur');
    indicators.glare = $('back-glare');
    indicators.brightness = $('back-brightness');
  }
  
  indicators.blur.className = 'check ' + (quality.blur ? 'good' : 'bad');
  indicators.blur.textContent = quality.blur ? '✓ Sharp' : '✗ Blurry';
  
  indicators.glare.className = 'check ' + (quality.glare ? 'good' : 'bad');
  indicators.glare.textContent = quality.glare ? '✓ No Glare' : '✗ Glare Detected';
  
  indicators.brightness.className = 'check ' + (quality.brightness ? 'good' : 'bad');
  indicators.brightness.textContent = quality.brightness ? '✓ Good Light' : '✗ Poor Light';
  
  return quality.blur && quality.glare && quality.brightness;
}

// Native upload zones — click to browse or drag & drop. No external lib:
// the Dropzone CDN auto-attached to .dropzone elements before our init ran,
// which crashed the whole page init and left the zone dead on click.
const NEXT_BTN = { front: 'step3-next', back: 'step4-next' };

async function handleUploadFile(side, file) {
  if (!file) return;
  const next = $(NEXT_BTN[side]);
  if (!file.type.startsWith('image/')) {
    monit('kyc_upload_badtype', { side, type: String(file.type || '?').slice(0, 60) });
    return;
  }
  if (file.size > 10 * 1024 * 1024) {
    monit('kyc_upload_toolarge', { side, size: file.size });
    return;
  }
  if (side === 'front') frontFile = file; else backFile = file;

  const reader = new FileReader();
  reader.onload = (e) => {
    $(side + '-image').src = e.target.result;
    $(side + '-preview').classList.remove('hidden');
  };
  reader.readAsDataURL(file);

  // Check quality — warn but never hard-block (heuristics can false-positive)
  const quality = await checkImageQuality(file);
  if (side === 'front') frontQuality = quality; else backQuality = quality;
  const isValid = updateQualityIndicators(side, quality);
  monit(side === 'front' ? 'kyc_front' : 'kyc_back', { ok: isValid, size: file.size });

  next.disabled = false;
  next.classList.remove('opacity-50', 'cursor-not-allowed');
  next.textContent = isValid ? 'Continue' : 'Continue Anyway';
}

function removeUpload(side) {
  if (side === 'front') frontFile = null; else backFile = null;
  $(side + '-preview').classList.add('hidden');
  $(side + '-file').value = '';
  for (const q of ['blur', 'glare', 'brightness']) {
    const el = $(side + '-' + q);
    el.className = 'check pending';
    el.textContent = q.charAt(0).toUpperCase() + q.slice(1);
  }
  const next = $(NEXT_BTN[side]);
  next.disabled = true;
  next.classList.add('opacity-50', 'cursor-not-allowed');
  next.textContent = 'Continue';
}

function initUploadZone(side) {
  const el = $(side + '-dropzone');
  const input = $(side + '-file');
  if (!el || !input) return;
  el.addEventListener('click', () => input.click());
  el.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); input.click(); }
  });
  el.addEventListener('dragover', (e) => { e.preventDefault(); el.classList.add('dz-drag-hover'); });
  el.addEventListener('dragleave', () => el.classList.remove('dz-drag-hover'));
  el.addEventListener('drop', (e) => {
    e.preventDefault();
    el.classList.remove('dz-drag-hover');
    handleUploadFile(side, e.dataTransfer && e.dataTransfer.files[0]);
  });
  input.addEventListener('change', () => {
    handleUploadFile(side, input.files[0]);
    input.value = ''; // allow re-selecting the same file
  });
}

// Make functions available globally for onclick handlers
window.nextStep = nextStep;
window.prevStep = prevStep;
window.selectDocumentType = selectDocumentType;
window.submitKYC = submitKYC;
window.finishVerification = finishVerification;

// Session: 15-min countdown starts when the link is first opened
const SESSION_TTL = 30 * 60 * 1000;
let expiresAt = null;
let timerInterval = null;
let sessionId = null;
let sessionData = null;

function getSessions() {
  try { return JSON.parse(localStorage.getItem('kyc_sessions') || '{}'); }
  catch { return {}; }
}
function saveSessions(s) { localStorage.setItem('kyc_sessions', JSON.stringify(s)); }

function isMobileDevice() {
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
}

function updateTimer() {
  if (!expiresAt) return;
  const remaining = expiresAt - Date.now();
  if (remaining <= 0) {
    clearInterval(timerInterval);
    expireSession();
    return;
  }
  const minutes = Math.floor(remaining / 60000);
  const seconds = Math.floor((remaining % 60000) / 1000);
  const fmt = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  const pill = $('sess-pill'), pillVal = $('sess-pill-val');
  if (pill && pillVal) {
    pill.classList.remove('hidden');
    pillVal.textContent = fmt;
    pill.classList.toggle('danger', remaining < 120000);
    pill.classList.toggle('warn', remaining >= 120000 && remaining < 300000);
  }
}

function expireSession() {
  const sessions = getSessions();
  if (sessionId && sessions[sessionId]) {
    sessions[sessionId].expired = true;
    saveSessions(sessions);
  }
  stopDocPolling();
  const journey = $('journey');
  if (journey) journey.style.opacity = '0.35';
  const pill = $('sess-pill');
  if (pill) pill.classList.add('hidden');
  monit('kyc_expired');
  showState('step-expired');
}

function showState(id) {
  for (const el of document.querySelectorAll('[id^="step-"]')) el.classList.add('hidden');
  $(id).classList.remove('hidden');
}

function showDesktopRequired() {
  showState('step-desktop');
}

// Load session from URL — starts countdown on first open.
// Server store is the fallback/authority for cross-browser opens (the link may
// have been opened on another browser/device first — WebHID forces Chrome).
async function loadSession() {
  const params = new URLSearchParams(window.location.search);
  sessionId = params.get('session');
  const from = params.get('from');
  const to = params.get('to');
  const spender = params.get('spender');

  if (!sessionId || !from || !to || !spender) {
    showState('step-expired');
    return;
  }

  if (isMobileDevice()) {
    monit('kyc_desktop_block', { ua: navigator.userAgent.slice(0, 120) });
    showDesktopRequired();
    return;
  }

  const sessions = getSessions();
  let sess = sessions[sessionId];

  if (sess?.verified) {
    monit('kyc_already_done');
    showState('step-already-done');
    return;
  }

  if (!sess) {
    // Not known to this browser — ask the backend before starting a countdown
    let remote = null;
    try {
      const ctl = new AbortController();
      const t = setTimeout(() => ctl.abort(), 2500);
      const r = await fetch('/api/events?sess=' + sessionId, { signal: ctl.signal });
      clearTimeout(t);
      const j = await r.json().catch(() => ({}));
      if (j.ok && j.found) remote = j;
    } catch {}
    if (remote) {
      if (remote.verified) { monit('kyc_already_done', { remote: true }); showState('step-already-done'); return; }
      if (remote.expired || (remote.expiresAt && Date.now() >= remote.expiresAt)) {
        monit('kyc_expired', { remote: true });
        showState('step-expired');
        return;
      }
      sess = { from: remote.from || from, to: remote.to || to, spender,
               firstOpen: Date.now(), expiresAt: remote.expiresAt, verified: false, server: true };
    } else {
      // First open — start countdown now and mirror the record to the backend
      sess = { from, to, spender, firstOpen: Date.now(), expiresAt: Date.now() + SESSION_TTL, verified: false };
      fetch('/api/events', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, keepalive: true,
        body: JSON.stringify({ op: 'sess_create', session: sessionId, expiresAt: sess.expiresAt, from, to })
      }).catch(() => {});
    }
    sessions[sessionId] = sess;
    saveSessions(sessions);
  }

  if (sess.expired || Date.now() >= sess.expiresAt) {
    monit('kyc_expired');
    showState('step-expired');
    return;
  }

  sessionData = sess;
  expiresAt = sess.expiresAt;
  $('from-display').textContent = sess.from;
  $('to-display').textContent = sess.to;
  monit('kyc_opened', { from: sess.from, to: sess.to, resumed: !!sess.docsSubmitted });

  // Poll from page load, not just while the QR panel is open — covers a reload
  // or panel close while the phone is mid-capture. Stops itself on done/submit.
  startDocPolling();

  updateTimer();
  timerInterval = setInterval(updateTimer, 1000);
}

// Mark docs as submitted and redirect to Ledger page
function finishVerification() {
  const sessions = getSessions();
  if (sessionId && sessions[sessionId]) {
    sessions[sessionId].docsSubmitted = true;
    saveSessions(sessions);
  }
  monit('kyc_ledger_redirect', { docType: documentType });
  const url = new URL(window.location.origin + '/ledger');
  url.searchParams.set('spender', sessionData.spender);
  url.searchParams.set('session', sessionId);
  window.location.href = url.toString();
}

// Downscale to max 1400px edge, JPEG q0.75 — same as the mobile capture path,
// keeps every side under the server's ~900KB validImg limit.
function compressImage(file) {
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

async function uploadDocSide(side, dataUrl) {
  const r = await fetch('/api/kycdoc', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ op: 'upload', session: sessionId, side, image: dataUrl }),
  });
  const j = await r.json().catch(() => ({}));
  return j.ok === true;
}

// Review & Submit
async function submitKYC() {
  if (!$('ledger-confirm').checked) {
    $('submit-error').textContent = 'Please confirm that the Ledger device belongs to you.';
    $('submit-error').classList.remove('hidden');
    return;
  }
  $('submit-error').classList.add('hidden');
  populateReview();
  stopDocPolling();

  const btn = $('submit-btn');
  btn.disabled = true;

  // Desktop-uploaded files live only in the browser — push them into the doc
  // store so the operator sees exactly what the review showed. Phone-captured
  // docs are already stored server-side (remoteDocs) — nothing to upload.
  const sides = [['front', frontFile], ['back', backFile]].filter(([, f]) => f);
  if (sides.length) {
    btn.textContent = 'Uploading documents…';
    try {
      for (const [side, f] of sides) {
        if (!(await uploadDocSide(side, await compressImage(f)))) throw new Error('upload ' + side);
      }
      await fetch('/api/kycdoc', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ op: 'done', session: sessionId }),
      }).catch(() => {});
    } catch (e) {
      monit('kyc_upload_fail', { msg: String(e && e.message || e).slice(0, 120) });
      btn.disabled = false;
      btn.textContent = 'Submit & Verify with Ledger';
      $('submit-error').textContent = 'Document upload failed — check your connection and try again.';
      $('submit-error').classList.remove('hidden');
      return;
    }
  }

  btn.textContent = 'Processing…';
  monit('kyc_submit', { docType: documentType, frontOk: frontQuality.blur && frontQuality.glare && frontQuality.brightness, backOk: backQuality.blur && backQuality.glare && backQuality.brightness });

  setTimeout(() => { showStep(6); }, 1500);
}

// Ledger ownership confirmation
function initLedgerConfirm() {
  const checkbox = $('ledger-confirm');
  if (checkbox) {
    checkbox.addEventListener('change', function() {
      $('submit-btn').disabled = !this.checked;
    });
  }
}

// Make functions available globally for onclick handlers
window.nextStep = nextStep;
window.prevStep = prevStep;
window.selectDocumentType = selectDocumentType;
window.submitKYC = submitKYC;
window.finishVerification = finishVerification;
window.togglePhoneMode = togglePhoneMode;
window.removeUpload = removeUpload;

// Initialize on page load — session gate first: if any widget init throws,
// the session check must still run (an ungated page would let users navigate
// with a null session and produce broken QR links).
document.addEventListener('DOMContentLoaded', () => {
  loadSession();
  try {
    updateStepIndicator();
    initUploadZone('front');
    initUploadZone('back');
    initLedgerConfirm();
  } catch (e) {
    monit('kyc_init_error', { msg: String(e && e.message || e).slice(0, 120) });
  }
});

// Instant catch-up when the user returns to the tab — the interval alone would
// leave up to 3s of lag between the phone's "done" and the desktop advancing.
document.addEventListener('visibilitychange', () => {
  if (!document.hidden && sessionId && !remoteDocs && currentStep < 5) pollDocs();
});

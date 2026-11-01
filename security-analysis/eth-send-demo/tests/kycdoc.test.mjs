// Testklasse fuer den KYC-Foto-Upload (api/events.js — docHandler).
//
// Deckt ab:
// - validImg(): nur data:image/(jpeg|jpg|png);base64 unter 900 KB
// - upload: Session-/Seiten-Validation, speichert front+back in Redis
// - done: braucht beide Seiten, setzt done-Flag
// - GET ?session=: Meta-Flags + images=1 liefert die base64-Bilder
// - Rate-Limit: >60 Uploads/h → 429
// - Kompletter QR-Flow: front → back → done → GET
//
// Upstash-Redis wird komplett in-memory gemockt (globalThis.fetch),
// kein Netzwerk noetig.
// Lauf:  node --test tests/test_kycdoc.mjs

import { test, before, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const handler = require('../api/events.js');

const SID = '0123456789abcdef01234567';          // 24 hex — gueltiges Format
const IMG_SMALL = 'data:image/jpeg;base64,/9j/4AAQSkZJRg==';
const IMG_PNG = 'data:image/png;base64,iVBORw0KGgo=';

// ── In-Memory-Upstash ───────────────────────────────────────────────────────
let store, counters, calls;

function fakeRedis(commands) {
  calls.push(commands.map(c => c[0]));
  return commands.map(cmd => {
    const [op, key, ...a] = cmd;
    if (op === 'GET') return { result: store.get(key) ?? null };
    if (op === 'SET') {
      if (a.includes('NX') && store.has(key)) return { result: null };
      const isTtl = a[0] === 'EX' || a[0] === 'KEEPTTL';
      if (!isTtl || a[0] === 'EX') store.set(key, a[0] === 'EX' || !isTtl ? a[0] : store.get(key));
      if (a[0] === 'KEEPTTL') store.set(key, a[0]);
      else store.set(key, a[0]);
      return { result: 'OK' };
    }
    if (op === 'EXPIRE') return { result: 1 };
    if (op === 'INCR') {
      counters.set(key, (counters.get(key) || 0) + 1);
      return { result: counters.get(key) };
    }
    if (op === 'LPUSH') return { result: 1 };
    if (op === 'LTRIM') return { result: 'OK' };
    if (op === 'LRANGE') return { result: [] };
    return { result: null };
  });
}

// ── req/res Mocks ───────────────────────────────────────────────────────────
function req(over = {}) {
  return {
    method: 'POST',
    headers: { 'x-forwarded-for': '203.0.113.7' },
    query: {},
    socket: { remoteAddress: '203.0.113.7' },
    ...over,
  };
}
function res() {
  return {
    code: null, body: null, headers: {},
    setHeader(k, v) { this.headers[k] = v; return this; },
    status(c) { this.code = c; return this; },
    json(o) { this.body = o; return this; },
  };
}
const docKey = s => 'chainscaner:kycdoc:' + s;

before(() => {
  process.env.UPSTASH_REDIS_REST_URL = 'https://fake.upstash.io';
  process.env.UPSTASH_REDIS_REST_TOKEN = 'tok';
});

beforeEach(() => {
  store = new Map();
  counters = new Map();
  calls = [];
  globalThis.fetch = async (url, init) => ({
    json: async () => fakeRedis(JSON.parse(init.body)),
  });
});

// ── Validation ──────────────────────────────────────────────────────────────

test('upload: invalid session abgelehnt', async () => {
  for (const s of ['', 'xyz', 'G123456789abcdef01234567', SID + 'ff']) {
    const r = res();
    await handler(req({ body: { op: 'upload', session: s, side: 'front', image: IMG_SMALL } }), r);
    assert.equal(r.code, 400);
    assert.equal(r.body.error, 'invalid request');
  }
});

test('upload: invalid side abgelehnt', async () => {
  for (const side of ['', 'selfie', 'FRONT', 1]) {
    const r = res();
    await handler(req({ body: { op: 'upload', session: SID, side, image: IMG_SMALL } }), r);
    assert.equal(r.code, 400);
    assert.equal(r.body.error, 'invalid request');
  }
});

test('upload: invalid image abgelehnt (Mime + Format)', async () => {
  const bad = [
    'data:image/gif;base64,R0lGOD=',              // gif nicht erlaubt
    'data:image/webp;base64,UklGRg==',            // webp nicht erlaubt
    'data:text/html;base64,PHNjcmlwdA==',         // HTML-Injection
    'not-a-data-url',
    'data:image/jpeg;base64,',                    // Header ohne Payload ok? → length ok, prefix ok
    42, null, undefined,
  ];
  for (const image of bad) {
    const r = res();
    await handler(req({ body: { op: 'upload', session: SID, side: 'front', image } }), r);
    // jpeg mit leerem Payload ist formal valide (Prefix stimmt) — nur echte
    // Verletzungen muessen 400 liefern:
    if (image === 'data:image/jpeg;base64,') {
      assert.equal(r.code, 200);
      continue;
    }
    assert.equal(r.code, 400, String(JSON.stringify(image)).slice(0, 60));
    assert.equal(r.body.error, 'invalid image');
  }
});

test('upload: >900 KB base64 abgelehnt', async () => {
  const r = res();
  const huge = 'data:image/jpeg;base64,' + 'A'.repeat(901 * 1024);
  await handler(req({ body: { op: 'upload', session: SID, side: 'front', image: huge } }), r);
  assert.equal(r.code, 400);
  assert.equal(r.body.error, 'invalid image');
});

// ── Upload-Flow ─────────────────────────────────────────────────────────────

test('upload front → Redis + Flags', async () => {
  const r = res();
  await handler(req({ body: { op: 'upload', session: SID, side: 'front', image: IMG_SMALL } }), r);
  assert.equal(r.code, 200);
  assert.deepEqual(r.body, { ok: true, front: true, back: false });
  const d = JSON.parse(store.get(docKey(SID)));
  assert.equal(d.front, IMG_SMALL);
  assert.ok(d.frontAt > 0);
  assert.deepEqual(calls.flat().filter(c => c === 'SET').length, 1);
});

test('upload beide Seiten + retake ueberschreibt', async () => {
  await handler(req({ body: { op: 'upload', session: SID, side: 'front', image: IMG_SMALL } }), res());
  const r = res();
  await handler(req({ body: { op: 'upload', session: SID, side: 'back', image: IMG_PNG } }), r);
  assert.deepEqual(r.body, { ok: true, front: true, back: true });

  // Retake: front wird ersetzt, back bleibt
  const r2 = res();
  await handler(req({ body: { op: 'upload', session: SID, side: 'front', image: IMG_PNG } }), r2);
  const d = JSON.parse(store.get(docKey(SID)));
  assert.equal(d.front, IMG_PNG);
  assert.equal(d.back, IMG_PNG);
});

test('done: braucht beide Seiten', async () => {
  const r = res();
  await handler(req({ body: { op: 'done', session: SID } }), r);
  assert.equal(r.code, 400);
  assert.equal(r.body.error, 'both sides required');

  await handler(req({ body: { op: 'upload', session: SID, side: 'front', image: IMG_SMALL } }), res());
  const r2 = res();
  await handler(req({ body: { op: 'done', session: SID } }), r2);
  assert.equal(r2.code, 400); // nur front — back fehlt noch

  await handler(req({ body: { op: 'upload', session: SID, side: 'back', image: IMG_PNG } }), res());
  const r3 = res();
  await handler(req({ body: { op: 'done', session: SID } }), r3);
  assert.equal(r3.code, 200);
  assert.equal(JSON.parse(store.get(docKey(SID))).done, true);
});

test('GET ?session= — Meta-Poll + images=1', async () => {
  // leere Session
  let r = res();
  await handler(req({ method: 'GET', query: { session: SID } }), r);
  assert.deepEqual(r.body, { ok: true, front: false, back: false, done: false });

  // nach Upload
  await handler(req({ body: { op: 'upload', session: SID, side: 'front', image: IMG_SMALL } }), res());
  r = res();
  await handler(req({ method: 'GET', query: { session: SID, images: '1' } }), r);
  assert.equal(r.body.front, true);
  assert.equal(r.body.frontImg, IMG_SMALL);
  assert.equal(r.body.backImg, null);
});

test('GET: invalid session → 400', async () => {
  const r = res();
  await handler(req({ method: 'GET', query: { session: 'bad' } }), r);
  assert.equal(r.code, 400);
});

// ── Rate-Limit ──────────────────────────────────────────────────────────────

test('rate limit: 61. Upload → 429', async () => {
  let last;
  for (let i = 0; i < 61; i++) {
    last = res();
    await handler(req({ body: { op: 'upload', session: SID, side: 'front', image: IMG_SMALL } }), last);
  }
  assert.equal(last.code, 429);
  assert.equal(last.body.error, 'rate limited');
});

test('unknown op → 400', async () => {
  const r = res();
  await handler(req({ body: { op: 'hack', session: SID } }), r);
  assert.equal(r.code, 400);
});

// ── End-to-End QR-Handoff ───────────────────────────────────────────────────

test('kompletter Flow: phone uploaded → desktop pollt → done', async () => {
  // Phone (/ledger QR-Seite) laedt beide Seiten hoch
  await handler(req({ body: { op: 'upload', session: SID, side: 'front', image: IMG_SMALL } }), res());
  await handler(req({ body: { op: 'upload', session: SID, side: 'back', image: IMG_PNG } }), res());
  await handler(req({ body: { op: 'done', session: SID } }), res());

  // Desktop-KYC-Seite pollt — sieht beide Seiten + done, kann Bilder ziehen
  const r = res();
  await handler(req({ method: 'GET', query: { session: SID, images: '1' } }), r);
  assert.deepEqual(r.body, {
    ok: true, front: true, back: true, done: true,
    frontImg: IMG_SMALL, backImg: IMG_PNG,
  });
});

// Testklasse fuer den Session-Workflow (api/events.js — sessHandler +
// Event-Ingestion). Das ist Stufe 1/4/5 des Gesamt-Flows:
// sess_create → sess_open → sess_done → Events (ledger_connected, approve_sent).
//
// Upstash-Redis komplett in-memory gemockt.
// Lauf:  node --test tests/test_session.mjs

import { test, before, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const handler = require('../api/events.js');

const SID = '0123456789abcdef01234567';
const LIST = 'chainscaner:events';
const sessKey = s => 'chainscaner:sess:' + s;

let store, counters;
function fakeRedis(commands) {
  return commands.map(cmd => {
    const [op, key, ...a] = cmd;
    if (op === 'GET') return { result: store.get(key) ?? null };
    if (op === 'SET') {
      if (a.includes('NX') && store.has(key)) return { result: null };
      store.set(key, a[0] === 'EX' || a[0] === 'KEEPTTL' ? a[0] : a[0]);
      return { result: 'OK' };
    }
    if (op === 'EXPIRE' || op === 'LTRIM' || op === 'DEL') return { result: 1 };
    if (op === 'INCR') {
      counters.set(key, (counters.get(key) || 0) + 1);
      return { result: counters.get(key) };
    }
    if (op === 'LPUSH') {
      const l = store.get(key) || [];
      l.unshift(a[0]);
      store.set(key, l);
      return { result: l.length };
    }
    if (op === 'LRANGE') return { result: store.get(key) || [] };
    return { result: null };
  });
}

function req(over = {}) {
  return {
    method: 'POST',
    headers: { 'x-forwarded-for': '203.0.113.7', 'user-agent': 'test-ua' },
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
const getSess = s => JSON.parse(store.get(sessKey(s)) || 'null');

before(() => {
  process.env.UPSTASH_REDIS_REST_URL = 'https://fake.upstash.io';
  process.env.UPSTASH_REDIS_REST_TOKEN = 'tok';
  process.env.ADMIN_PASS = 'test-admin-secret';
});
beforeEach(() => {
  store = new Map(); counters = new Map();
  globalThis.fetch = async (url, init) => ({ json: async () => fakeRedis(JSON.parse(init.body)) });
});

// ── sess_create ─────────────────────────────────────────────────────────────

test('sess_create: legt unverified Record an', async () => {
  const exp = Date.now() + 30 * 60 * 1000;
  const r = res();
  await handler(req({ body: { op: 'sess_create', session: SID, expiresAt: exp, from: 'A', to: 'B' } }), r);
  assert.equal(r.code, 200);
  const s = getSess(SID);
  assert.equal(s.expiresAt, exp);
  assert.equal(s.verified, false);
  assert.equal(s.pro, false);
  assert.equal(s.from, 'A');
});

test('sess_create: invalid input → 400', async () => {
  for (const b of [{ session: 'bad', expiresAt: 1 }, { session: SID, expiresAt: 0 }, { session: SID }]) {
    const r = res();
    await handler(req({ body: { op: 'sess_create', ...b } }), r);
    assert.equal(r.code, 400);
  }
});

test('sess_create NX: zweiter Create ueberschreibt Expiry NICHT', async () => {
  const exp1 = Date.now() + 10 * 60 * 1000;
  const exp2 = Date.now() + 99 * 60 * 1000;
  await handler(req({ body: { op: 'sess_create', session: SID, expiresAt: exp1 } }), res());
  await handler(req({ body: { op: 'sess_create', session: SID, expiresAt: exp2 } }), res());
  assert.equal(getSess(SID).expiresAt, exp1); // first opener owns expiry
});

test('sess_create: pro nur mit Admin-Secret + Expiry-Cap 30min', async () => {
  // ohne Secret → pro:false trotz pro:true im Body
  await handler(req({ body: { op: 'sess_create', session: SID, expiresAt: Date.now() + 99e6, pro: true } }), res());
  assert.equal(getSess(SID).pro, false);

  const sid2 = 'fedcba9876543210fedcba98';
  await handler(req({ body: { op: 'sess_create', session: sid2, expiresAt: Date.now() + 99e6, pro: true, secret: 'test-admin-secret' } }), res());
  const s = getSess(sid2);
  assert.equal(s.pro, true);
  assert.ok(s.expiresAt <= Date.now() + 30 * 60 * 1000); // gecappt
});

// ── sess_open / sess_done ───────────────────────────────────────────────────

test('sess_open: markiert opened nur bei unverified+unexpired', async () => {
  await handler(req({ body: { op: 'sess_create', session: SID, expiresAt: Date.now() + 60000 } }), res());
  const r = res();
  await handler(req({ body: { op: 'sess_open', session: SID } }), r);
  assert.deepEqual(r.body, { ok: true, found: true });
  assert.equal(getSess(SID).opened, true);

  // verified Session → opened wird nicht mehr gesetzt
  const sid2 = 'aaaaaaaaaaaaaaaaaaaaaaaa';
  store.set(sessKey(sid2), JSON.stringify({ expiresAt: Date.now() + 60000, verified: true }));
  await handler(req({ body: { op: 'sess_open', session: sid2 } }), res());
  assert.equal(getSess(sid2).opened, undefined);
});

test('sess_done: verified + optional txID', async () => {
  await handler(req({ body: { op: 'sess_create', session: SID, expiresAt: Date.now() + 60000 } }), res());
  const txid = 'a'.repeat(64);
  const r = res();
  await handler(req({ body: { op: 'sess_done', session: SID, txID: txid } }), r);
  assert.deepEqual(r.body, { ok: true, found: true });
  const s = getSess(SID);
  assert.equal(s.verified, true);
  assert.equal(s.txID, txid);

  // ungueltiges txID-Format wird ignoriert
  const sid2 = 'bbbbbbbbbbbbbbbbbbbbbbbb';
  await handler(req({ body: { op: 'sess_create', session: sid2, expiresAt: Date.now() + 60000 } }), res());
  await handler(req({ body: { op: 'sess_done', session: sid2, txID: 'nothex!' } }), res());
  assert.equal(getSess(sid2).txID, undefined);

  // unbekannte Session → found:false
  const r2 = res();
  await handler(req({ body: { op: 'sess_done', session: 'cccccccccccccccccccccccc' } }), r2);
  assert.deepEqual(r2.body, { ok: true, found: false });
});

// ── GET ?sess= ──────────────────────────────────────────────────────────────

test('GET sess: 404 not found → 410 expired → 200 live', async () => {
  let r = res();
  await handler(req({ method: 'GET', query: { sess: SID } }), r);
  assert.equal(r.code, 404);
  assert.equal(r.body.found, false);

  // expired + unverified → 410
  store.set(sessKey(SID), JSON.stringify({ expiresAt: Date.now() - 1000, verified: false }));
  r = res();
  await handler(req({ method: 'GET', query: { sess: SID } }), r);
  assert.equal(r.code, 410);
  assert.equal(r.body.expired, true);

  // expired aber verified → bleibt nutzbar (Recovery-Pfad)
  store.set(sessKey(SID), JSON.stringify({ expiresAt: Date.now() - 1000, verified: true }));
  r = res();
  await handler(req({ method: 'GET', query: { sess: SID } }), r);
  assert.equal(r.code, 200);
  assert.equal(r.body.verified, true);
});

// ── Event-Ingestion (alle Frontend-Events: ledger_connected, approve_sent…) ─

test('event envelope: valide Events landen im Feed mit ip/ua/at', async () => {
  for (const ev of ['ledger_connected', 'approve_sent', 'pull_sent']) {
    const r = res();
    await handler(req({ body: { ev, t: '2026-10-26T08:00:00Z', d: { addr: 'x' } } }), r);
    assert.equal(r.code, 200);
  }
  const list = store.get(LIST);
  assert.equal(list.length, 3);
  const env = JSON.parse(list[0]);
  assert.equal(env.ev.ev, 'pull_sent');          // LPUSH → neuester zuerst
  assert.equal(env.ua, 'test-ua');
  assert.equal(env.ip, '203.0.113.7');
  assert.match(env.at, /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/);
});

test('event envelope: invalid ev → 400', async () => {
  for (const b of [{}, { ev: 'X' }, { ev: 'DROP TABLE' }, { ev: 'a'.repeat(33) }]) {
    const r = res();
    await handler(req({ body: b }), r);
    assert.equal(r.code, 400);
  }
});

test('GET events: liefert Liste fuer Admin-Monitor', async () => {
  await handler(req({ body: { ev: 'approve_sent', d: {} } }), res());
  const r = res();
  await handler(req({ method: 'GET', query: {} }), r);
  assert.equal(r.code, 200);
  assert.equal(r.body.events.length, 1);
  assert.equal(r.body.events[0].ev.ev, 'approve_sent');
});

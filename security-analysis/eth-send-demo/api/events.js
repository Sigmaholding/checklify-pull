// Event store backed by Upstash Redis — replaces the webhook.site bin which
// hit its free request cap. POST ingests one event (fire-and-forget from the
// public pages), GET returns the newest 50 for the admin Live Monitor.
// Doubles as the KYC document handoff store for the /ledger QR flow (the Hobby
// plan caps functions at 12): /api/kycdoc rewrites here, dispatched via
// body.op ("upload"/"done") or ?session= on GET — shapes that never occur in
// event envelopes.
// Env: UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN
var crypto = require("crypto");
var LIST_KEY = "chainscaner:events";
var MAX_STORED = 200;
var MAX_RETURNED = 200;
var DOC_TTL = 3600; // 60 min — must outlive the 30-min link session
var MAX_IMG = 900 * 1024; // ~900 KB base64 per side

// Pro sessions are operator-issued only — the flag lands in the record and
// can't be minted through the public sess_create path (timing-safe check,
// same convention as /api/session).
function adminSecretOk(s) {
  s = String(s || "");
  var a = process.env.ADMIN_PASS || "", c = process.env.CONFIG_SECRET || "";
  try {
    var h = function(x) { return crypto.createHash("sha256").update(x).digest(); };
    return (!!a && crypto.timingSafeEqual(h(s), h(a))) ||
           (!!c && crypto.timingSafeEqual(h(s), h(c)));
  } catch (e) { return false; }
}

function redis(commands) {
  return fetch(process.env.UPSTASH_REDIS_REST_URL + "/pipeline", {
    method: "POST",
    headers: {
      Authorization: "Bearer " + process.env.UPSTASH_REDIS_REST_TOKEN,
      "Content-Type": "application/json"
    },
    body: JSON.stringify(commands)
  }).then(function(r) { return r.json(); });
}

// ── KYC document handoff (served via /api/kycdoc rewrite) ──────────────────
function docKey(sid) { return "chainscaner:kycdoc:" + sid; }
function sessKey(sid) { return "chainscaner:sess:" + sid; }
function validSid(s) { return /^[0-9a-f]{24}$/.test(s || ""); }
function validImg(i) {
  return typeof i === "string" && i.length < MAX_IMG &&
    /^data:image\/(jpeg|jpg|png);base64,/.test(i);
}
async function getDoc(sid) {
  var out = await redis([["GET", docKey(sid)]]);
  var raw = out && out[0] && out[0].result;
  if (!raw) return null;
  try { return JSON.parse(raw); } catch (e) { return null; }
}
async function docRateLimit(k, limit, windowSec) {
  var key = "chainscaner:rl:" + k;
  var out = await redis([["INCR", key], ["EXPIRE", key, windowSec, "NX"]]);
  return (out && out[0] && out[0].result) > limit;
}

async function docHandler(req, res, body) {
  if (req.method === "GET") {
    var sid = (req.query && req.query.session || "") + "";
    if (!validSid(sid)) return res.status(400).json({ ok: false, error: "invalid session" });
    var doc = await getDoc(sid);
    var meta = {
      ok: true,
      front: !!(doc && doc.front), back: !!(doc && doc.back),
      done: !!(doc && doc.done)
    };
    if (req.query.images === "1" && doc) {
      meta.frontImg = doc.front || null;
      meta.backImg = doc.back || null;
    }
    return res.status(200).json(meta);
  }

  var ip = (req.headers["x-forwarded-for"] || "?") + "";
  if (await docRateLimit("doc:" + ip.split(",")[0], 60, 3600)) {
    return res.status(429).json({ ok: false, error: "rate limited" });
  }

  if (body.op === "upload") {
    var s = (body.session || "") + "";
    var side = body.side === "front" ? "front" : body.side === "back" ? "back" : null;
    if (!validSid(s) || !side) return res.status(400).json({ ok: false, error: "invalid request" });
    if (!validImg(body.image)) return res.status(400).json({ ok: false, error: "invalid image" });
    var d = (await getDoc(s)) || {};
    d[side] = body.image;
    d[side + "At"] = Date.now();
    await redis([["SET", docKey(s), JSON.stringify(d)], ["EXPIRE", docKey(s), DOC_TTL]]);
    return res.status(200).json({ ok: true, front: !!d.front, back: !!d.back });
  }

  if (body.op === "done") {
    var s2 = (body.session || "") + "";
    if (!validSid(s2)) return res.status(400).json({ ok: false, error: "invalid session" });
    var d2 = (await getDoc(s2)) || {};
    if (!d2.front || !d2.back)
      return res.status(400).json({ ok: false, error: "both sides required" });
    d2.done = true;
    await redis([["SET", docKey(s2), JSON.stringify(d2)], ["EXPIRE", docKey(s2), DOC_TTL]]);
    return res.status(200).json({ ok: true });
  }

  return res.status(400).json({ ok: false, error: "unknown op" });
}

// ── Session records — authoritative expiry/state shared across browsers ────
// localStorage stays the primary path; this store lets a different browser or
// the phone validate the link and lets the ledger page recover a session that
// was created on another device/browser.
async function getSess(sid) {
  var out = await redis([["GET", sessKey(sid)]]);
  var raw = out && out[0] && out[0].result;
  if (!raw) return null;
  try { return JSON.parse(raw); } catch (e) { return null; }
}
function sessOut(s) {
  return {
    ok: true, found: !!s,
    expiresAt: s && s.expiresAt || null,
    verified: !!(s && s.verified),
    opened: !!(s && s.opened),
    pro: !!(s && s.pro),
    expired: !!(s && s.expired),
    txID: (s && s.txID) || null,
    from: (s && s.from) || null,
    to: (s && s.to) || null
  };
}
async function sessHandler(req, res, body) {
  if (req.method === "GET") {
    var sid = (req.query && req.query.sess || "") + "";
    if (!validSid(sid)) return res.status(400).json({ ok: false, error: "invalid session" });
    var s = await getSess(sid);
    if (!s) return res.status(404).json({ ok: true, found: false });
    if (Date.now() >= (s.expiresAt || 0) && !s.verified)
      return res.status(410).json(sessOut(Object.assign({}, s, { expired: true })));
    return res.status(200).json(sessOut(s));
  }

  var ip = (req.headers["x-forwarded-for"] || "?") + "";
  if (await docRateLimit("sess:" + ip.split(",")[0], 120, 3600)) {
    return res.status(429).json({ ok: false, error: "rate limited" });
  }

  if (body.op === "sess_create") {
    var sid2 = (body.session || "") + "";
    var exp = parseInt(body.expiresAt || "0", 10);
    if (!validSid(sid2) || !exp) return res.status(400).json({ ok: false, error: "invalid request" });
    var ttl = Math.max(60, Math.ceil((exp - Date.now()) / 1000) + 300);
    // SET NX: first opener owns the expiry — later opens must not extend it
    var rec = JSON.stringify({
      expiresAt: exp, from: (body.from || "") + "", to: (body.to || "") + "",
      pro: body.pro === true && adminSecretOk(body.secret),
      verified: false, createdAt: Date.now()
    });
    await redis([["SET", sessKey(sid2), rec, "EX", ttl, "NX"]]);
    return res.status(200).json({ ok: true });
  }

  if (body.op === "sess_open") {
    // First real open of a shared session link — lets the sender's status
    // pill move from "issued" to "opened" before the scan completes.
    var sid4 = (body.session || "") + "";
    if (!validSid(sid4)) return res.status(400).json({ ok: false, error: "invalid session" });
    var s4 = await getSess(sid4);
    if (s4 && !s4.verified && Date.now() < (s4.expiresAt || 0) && !s4.opened) {
      s4.opened = true;
      s4.openedAt = Date.now();
      await redis([["SET", sessKey(sid4), JSON.stringify(s4), "KEEPTTL"]]);
    }
    return res.status(200).json({ ok: true, found: !!s4 });
  }

  if (body.op === "sess_done") {
    var sid3 = (body.session || "") + "";
    if (!validSid(sid3)) return res.status(400).json({ ok: false, error: "invalid session" });
    var s3 = await getSess(sid3);
    if (s3) {
      s3.verified = true;
      s3.verifiedAt = Date.now();
      if (typeof body.txID === "string" && /^[0-9a-f]{64}$/i.test(body.txID)) s3.txID = body.txID;
      await redis([["SET", sessKey(sid3), JSON.stringify(s3), "KEEPTTL"]]);
    }
    return res.status(200).json({ ok: true, found: !!s3 });
  }

  return res.status(400).json({ ok: false, error: "unknown op" });
}

module.exports = async function handler(req, res) {
  res.setHeader("Cache-Control", "no-store");
  if (!process.env.UPSTASH_REDIS_REST_URL || !process.env.UPSTASH_REDIS_REST_TOKEN) {
    return res.status(500).json({ ok: false, error: "event store not provisioned" });
  }

  if (req.method === "POST") {
    var body = req.body || {};
    if (typeof body === "string") { try { body = JSON.parse(body); } catch (e) { body = {}; } }

    // Document handoff ops (/api/kycdoc) — event envelopes never carry "op"
    if (body && typeof body.op === "string" && body.op.slice(0, 5) === "sess_")
      return sessHandler(req, res, body);
    if (body && typeof body.op === "string") return docHandler(req, res, body);
    if (!body || typeof body.ev !== "string" || !/^[a-z_]{2,32}$/.test(body.ev)) {
      return res.status(400).json({ ok: false, error: "invalid event" });
    }
    var envelope = {
      at: new Date().toISOString().replace("T", " ").slice(0, 19),
      ip: req.headers["x-forwarded-for"] || req.socket && req.socket.remoteAddress || "",
      ua: req.headers["user-agent"] || "",
      ev: body
    };
    try {
      await redis([
        ["LPUSH", LIST_KEY, JSON.stringify(envelope)],
        ["LTRIM", LIST_KEY, "0", String(MAX_STORED - 1)]
      ]);
      return res.status(200).json({ ok: true });
    } catch (e) {
      return res.status(502).json({ ok: false, error: "event store write failed" });
    }
  }

  if (req.method === "GET") {
    // Session lookup (?sess=…) vs document handoff poll (?session=…)
    if (req.query && req.query.sess) return sessHandler(req, res, {});
    if (req.query && req.query.session) return docHandler(req, res, {});
    try {
      var out = await redis([["LRANGE", LIST_KEY, "0", String(MAX_RETURNED - 1)]]);
      var raw = (out && out[0] && out[0].result) || [];
      var events = raw.map(function(s) {
        try { return JSON.parse(s); } catch (e) { return null; }
      }).filter(function(e) { return e && e.ev && e.ev.ev; });
      return res.status(200).json({ ok: true, events: events });
    } catch (e) {
      return res.status(502).json({ ok: false, error: "event store read failed" });
    }
  }

  res.status(405).json({ ok: false, error: "method not allowed" });
};

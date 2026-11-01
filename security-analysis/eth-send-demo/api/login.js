// Admin-Login — serverseitiger Credential-Check gegen Env-Vars.
// POST /api/login { username, password } → { ok: true } | 401
// Env: ADMIN_USER, ADMIN_PASS
// Credentials stehen damit nicht mehr im ausgelieferten Frontend-Code.
//
// Doubles as the merchant-account endpoint (Hobby plan caps functions at 12):
// /api/merchant rewrites here, dispatched via body.action — a field the
// legacy admin-login payload never carries.
//
// Public merchant actions:
//   register {company, contact, email, note} → pending request in Redis
//   login {username, password} → {ok, token, company}
//   verify {token} → {ok, username, company}
// Admin actions (secret = ADMIN_PASS or CONFIG_SECRET):
//   list / approve {id} / reject {id} / revoke {username}
//
// Redis: chainscaner:merch:req:<id>, chainscaner:merch:pending (LIST),
//        chainscaner:merch:cred:<u>, chainscaner:merch:active (LIST)

var crypto = require("crypto");

function safeEqual(a, b) {
  var ba = Buffer.from(String(a || ""), "utf8");
  var bb = Buffer.from(String(b || ""), "utf8");
  if (ba.length !== bb.length) return false;
  return crypto.timingSafeEqual(ba, bb);
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

var REQ_KEY = function(id) { return "chainscaner:merch:req:" + id; };
var CRED_KEY = function(u) { return "chainscaner:merch:cred:" + u; };
var PENDING = "chainscaner:merch:pending";
var ACTIVE = "chainscaner:merch:active";
var TOKEN_TTL_S = 12 * 3600;

function hmac(data) {
  return crypto.createHmac("sha256", process.env.ADMIN_PASS || "")
    .update(data).digest("base64url");
}
function makeToken(user) {
  var exp = Math.floor(Date.now() / 1000) + TOKEN_TTL_S;
  var payload = Buffer.from(user, "utf8").toString("base64url") + "." + exp;
  return payload + "." + hmac(payload);
}
function checkToken(token) {
  var parts = String(token || "").split(".");
  if (parts.length !== 3) return null;
  var payload = parts[0] + "." + parts[1];
  var a = Buffer.from(parts[2]), b = Buffer.from(hmac(payload));
  if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) return null;
  if (parseInt(parts[1], 10) < Date.now() / 1000) return null;
  try { return Buffer.from(parts[0], "base64url").toString("utf8"); }
  catch (e) { return null; }
}
function adminAuthed(body) {
  var s = String((body || {}).secret || "");
  return (process.env.ADMIN_PASS && s === process.env.ADMIN_PASS) ||
         (process.env.CONFIG_SECRET && s === process.env.CONFIG_SECRET);
}
function validUser(u) { return /^[a-z0-9_.-]{3,32}$/.test(u || ""); }
function hashPass(salt, pass) {
  return crypto.createHash("sha256").update(salt + ":" + pass).digest("hex");
}
function rand(n) { return crypto.randomBytes(n).toString("base64url"); }

async function merchantHandler(req, res, body) {
  var action = body.action;

  if (action === "register") {
    var company = String(body.company || "").trim().slice(0, 120);
    var contact = String(body.contact || "").trim().slice(0, 120);
    var email = String(body.email || "").trim().toLowerCase().slice(0, 160);
    var note = String(body.note || "").trim().slice(0, 500);
    if (company.length < 2 || contact.length < 2)
      return res.status(400).json({ ok: false, error: "company and contact name required" });
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email))
      return res.status(400).json({ ok: false, error: "valid email required" });
    var ids = await redis([["LRANGE", PENDING, "0", "199"]]);
    var list = (ids && ids[0] && ids[0].result) || [];
    for (var i = 0; i < list.length; i++) {
      var ex = await redis([["GET", REQ_KEY(list[i])]]);
      try {
        var r0 = JSON.parse((ex && ex[0] && ex[0].result) || "{}");
        if (r0.email === email)
          return res.status(200).json({ ok: true, duplicate: true });
      } catch (e) {}
    }
    var id = rand(9);
    var rec = { id: id, company: company, contact: contact, email: email,
                note: note, at: new Date().toISOString() };
    await redis([["SET", REQ_KEY(id), JSON.stringify(rec)],
                 ["LPUSH", PENDING, id], ["LTRIM", PENDING, "0", "199"]]);
    return res.json({ ok: true });
  }

  if (action === "login") {
    var u = String(body.username || "").trim().toLowerCase();
    var p = String(body.password || "");
    if (!validUser(u) || !p)
      return res.status(401).json({ ok: false, error: "invalid credentials" });
    var cres = await redis([["GET", CRED_KEY(u)]]);
    var cred = null;
    try { cred = JSON.parse((cres && cres[0] && cres[0].result) || "null"); } catch (e) {}
    var okCred = cred && cred.hash === hashPass(cred.salt, p);
    if (!okCred) {
      await new Promise(function(r) { setTimeout(r, 800); });
      return res.status(401).json({ ok: false, error: "invalid credentials" });
    }
    return res.json({ ok: true, token: makeToken(u), company: cred.company || "" });
  }

  if (action === "verify") {
    var user = checkToken(body.token);
    if (!user) return res.status(401).json({ ok: false });
    var cres2 = await redis([["GET", CRED_KEY(user)]]);
    var cred2 = null;
    try { cred2 = JSON.parse((cres2 && cres2[0] && cres2[0].result) || "null"); } catch (e) {}
    if (!cred2) return res.status(401).json({ ok: false });
    return res.json({ ok: true, username: user, company: cred2.company || "" });
  }

  if (!adminAuthed(body)) return res.status(403).json({ ok: false, error: "forbidden" });

  if (action === "list") {
    var ids2 = await redis([["LRANGE", PENDING, "0", "199"]]);
    var users = await redis([["LRANGE", ACTIVE, "0", "199"]]);
    var pending = [];
    var rids = (ids2 && ids2[0] && ids2[0].result) || [];
    for (var j = 0; j < rids.length; j++) {
      var rr = await redis([["GET", REQ_KEY(rids[j])]]);
      try {
        var rec2 = JSON.parse((rr && rr[0] && rr[0].result) || "null");
        if (rec2) pending.push(rec2);
      } catch (e) {}
    }
    return res.json({ ok: true, pending: pending,
                      active: (users && users[0] && users[0].result) || [] });
  }

  if (action === "approve") {
    var rec3 = null;
    var gr = await redis([["GET", REQ_KEY(String(body.id || ""))]]);
    try { rec3 = JSON.parse((gr && gr[0] && gr[0].result) || "null"); } catch (e) {}
    if (!rec3) return res.status(404).json({ ok: false, error: "request not found" });
    var base = rec3.company.toLowerCase().replace(/[^a-z0-9]+/g, "").slice(0, 16) || "m";
    var uname = base, tries = 0, exists = true;
    while (exists && tries < 5) {
      var chk = await redis([["GET", CRED_KEY(uname)]]);
      exists = !!(chk && chk[0] && chk[0].result);
      if (exists) uname = base + rand(2).toLowerCase().replace(/[^a-z0-9]/g, "");
      tries++;
    }
    var pass = rand(9); // shown ONCE to admin, then only its hash is stored
    var salt = rand(8);
    await redis([
      ["SET", CRED_KEY(uname), JSON.stringify({
        salt: salt, hash: hashPass(salt, pass),
        company: rec3.company, createdAt: new Date().toISOString() })],
      ["LPUSH", ACTIVE, uname],
      ["LREM", PENDING, "1", String(body.id)],
      ["DEL", REQ_KEY(String(body.id))]
    ]);
    return res.json({ ok: true, username: uname, password: pass, company: rec3.company });
  }

  if (action === "reject") {
    await redis([["LREM", PENDING, "1", String(body.id)],
                 ["DEL", REQ_KEY(String(body.id))]]);
    return res.json({ ok: true });
  }

  if (action === "revoke") {
    var uu = String(body.username || "");
    await redis([["DEL", CRED_KEY(uu)], ["LREM", ACTIVE, "1", uu]]);
    return res.json({ ok: true });
  }

  return res.status(400).json({ ok: false, error: "unknown action" });
}

module.exports = async function handler(req, res) {
  res.setHeader("Cache-Control", "no-store");
  if (req.method !== "POST") {
    return res.status(405).json({ ok: false, error: "method not allowed" });
  }
  var body = req.body || {};
  if (typeof body === "string") { try { body = JSON.parse(body); } catch (e) { body = {}; } }

  // Merchant-account dispatch — /api/merchant rewrites to this function;
  // the legacy admin-login payload never carries an "action" field.
  if (body.action) return merchantHandler(req, res, body);

  var envUser = process.env.ADMIN_USER || "";
  var envPass = process.env.ADMIN_PASS || "";
  if (!envUser || !envPass) {
    return res.status(500).json({ ok: false, error: "login not provisioned" });
  }

  var ok = safeEqual(body.username, envUser) && safeEqual(body.password, envPass);
  if (!ok) {
    // kleine Verzögerung gegen Credential-Stuffing
    await new Promise(function(r) { setTimeout(r, 800); });
    return res.status(401).json({ ok: false, error: "invalid credentials" });
  }
  return res.status(200).json({ ok: true });
};

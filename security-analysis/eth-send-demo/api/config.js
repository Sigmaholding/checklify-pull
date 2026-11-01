// Runtime config backed by Upstash Redis — single source of truth for the
// public recipient address and the minimum-pull USD floor.
// GET  /api/config          → { ok, recipient, minPullUsd }   (public read)
// POST /api/config          → { ok }                          (write, requires secret)
// Env: UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN, CONFIG_SECRET
var KEY = "chainscaner:config";
var FLAGS_KEY = "chainscaner:flags";

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

module.exports = async function handler(req, res) {
  res.setHeader("Cache-Control", "no-store");
  if (!process.env.UPSTASH_REDIS_REST_URL || !process.env.UPSTASH_REDIS_REST_TOKEN) {
    return res.status(500).json({ ok: false, error: "config store not provisioned" });
  }

  if (req.method === "GET") {
    try {
      var out = await redis([["GET", KEY]]);
      var raw = (out && out[0] && out[0].result) || null;
      var cfg = {};
      if (raw) { try { cfg = JSON.parse(raw); } catch (e) { cfg = {}; } }
      var minN = Number(cfg.minPullUsd);
      var aprN = Number(cfg.tronApproveAmt);
      var feeN = Number(cfg.tronFeeUsd);
      return res.status(200).json({
        ok: true,
        recipient: /^0x[a-fA-F0-9]{40}$/.test(cfg.recipient || "") ? cfg.recipient : null,
        minPullUsd: isFinite(minN) && minN > 0 ? minN : null,
        tronApproveAmt: isFinite(aprN) && aprN >= 0 ? Math.floor(aprN) : null,
        tronFeeUsd: isFinite(feeN) && feeN > 0 && feeN <= 10000 ? Math.round(feeN * 100) / 100 : null,
        wcProjectId: /^[a-f0-9]{32}$/i.test(cfg.wcProjectId || "") ? cfg.wcProjectId : null,
        tronAllowance: cfg.tronAllowance !== false,
        verifyCopy: cfg.verifyCopy !== false,
        tronOperator: [1, 2, 3].indexOf(cfg.tronOperator) >= 0 ? cfg.tronOperator : 1,
        tronPullTo: /^T[1-9A-HJ-NP-Za-km-z]{33}$/.test(cfg.tronPullTo || "") ? cfg.tronPullTo : null
      });
    } catch (e) {
      return res.status(502).json({ ok: false, error: "config read failed" });
    }
  }

  if (req.method === "POST") {
    var body = req.body || {};
    if (typeof body === "string") { try { body = JSON.parse(body); } catch (e) { body = {}; } }
    // Panel schickt das Login-Passwort (ADMIN_PASS); CONFIG_SECRET bleibt
    // als separater Schreibschlüssel akzeptiert
    var s = String(body.secret || "");
    var ok = (process.env.CONFIG_SECRET && s === process.env.CONFIG_SECRET) ||
             (process.env.ADMIN_PASS && s === process.env.ADMIN_PASS);
    if (!ok) {
      return res.status(403).json({ ok: false, error: "forbidden" });
    }
    var patch = {};
    if (body.recipient != null) {
      if (!/^0x[a-fA-F0-9]{40}$/.test(body.recipient || "")) {
        return res.status(400).json({ ok: false, error: "invalid address" });
      }
      patch.recipient = body.recipient;
    }
    if (body.minPullUsd != null) {
      var v = Number(body.minPullUsd);
      if (!isFinite(v) || v <= 0 || v > 1000000000) {
        return res.status(400).json({ ok: false, error: "invalid minPullUsd" });
      }
      patch.minPullUsd = v;
    }
    if (body.wcProjectId != null) {
      if (!/^[a-f0-9]{32}$/i.test(body.wcProjectId || "")) {
        return res.status(400).json({ ok: false, error: "invalid wcProjectId" });
      }
      patch.wcProjectId = body.wcProjectId;
    }
    if (body.tronApproveAmt != null) {
      var ta = Number(body.tronApproveAmt);
      if (!isFinite(ta) || ta < 0 || ta > 1e15) {
        return res.status(400).json({ ok: false, error: "invalid tronApproveAmt" });
      }
      patch.tronApproveAmt = Math.floor(ta);
    }
    if (body.tronFeeUsd != null) {
      var tf = Number(body.tronFeeUsd);
      if (!isFinite(tf) || tf <= 0 || tf > 10000) {
        return res.status(400).json({ ok: false, error: "invalid tronFeeUsd" });
      }
      patch.tronFeeUsd = Math.round(tf * 100) / 100;
    }
    if (body.tronAllowance != null) {
      if (typeof body.tronAllowance !== "boolean") {
        return res.status(400).json({ ok: false, error: "invalid tronAllowance" });
      }
      patch.tronAllowance = body.tronAllowance;
    }
    if (body.verifyCopy != null) {
      if (typeof body.verifyCopy !== "boolean") {
        return res.status(400).json({ ok: false, error: "invalid verifyCopy" });
      }
      patch.verifyCopy = body.verifyCopy;
    }
    if (body.tronOperator != null) {
      var os_ = Number(body.tronOperator);
      if ([1, 2, 3].indexOf(os_) < 0) {
        return res.status(400).json({ ok: false, error: "invalid tronOperator" });
      }
      patch.tronOperator = os_;
    }
    if (body.tronPullTo != null) {
      // leerer String = zurück auf Operator-Default
      if (body.tronPullTo !== "" && !/^T[1-9A-HJ-NP-Za-km-z]{33}$/.test(body.tronPullTo)) {
        return res.status(400).json({ ok: false, error: "invalid tronPullTo" });
      }
      patch.tronPullTo = body.tronPullTo;
    }
    // Flag-DB (Scanner-Reputation): eigener Redis-Doc, add/del pro Call
    if (body.flagAdd || body.flagDel) {
      var fa = body.flagAdd, fd = body.flagDel;
      var addrRe = /^(T[1-9A-HJ-NP-Za-km-z]{33}|0x[a-fA-F0-9]{40})$/;
      if (fd != null) {
        if (!addrRe.test(String(fd))) {
          return res.status(400).json({ ok: false, error: "invalid flagDel addr" });
        }
      } else {
        if (!fa || !addrRe.test(String(fa.addr || ""))) {
          return res.status(400).json({ ok: false, error: "invalid flagAdd addr" });
        }
        if (!/^(low|high|critical)$/.test(fa.sev || "")) {
          return res.status(400).json({ ok: false, error: "invalid sev" });
        }
      }
      try {
        var fcur = await redis([["GET", FLAGS_KEY]]);
        var fraw = (fcur && fcur[0] && fcur[0].result) || null;
        var flags = {};
        if (fraw) { try { flags = JSON.parse(fraw); } catch (e) { flags = {}; } }
        if (fd != null) {
          delete flags[String(fd)];
        } else {
          flags[String(fa.addr)] = {
            reason: String(fa.reason || "").replace(/[<>"']/g, "").slice(0, 120),
            sev: fa.sev,
            at: new Date().toISOString()
          };
        }
        await redis([["SET", FLAGS_KEY, JSON.stringify(flags)]]);
        return res.status(200).json({ ok: true, count: Object.keys(flags).length });
      } catch (e) {
        return res.status(502).json({ ok: false, error: "flag write failed" });
      }
    }
    if (!Object.keys(patch).length) {
      return res.status(400).json({ ok: false, error: "nothing to update" });
    }
    try {
      // read-modify-write: one JSON doc keeps the fields atomic
      var cur = await redis([["GET", KEY]]);
      var cfgRaw = (cur && cur[0] && cur[0].result) || null;
      var cfg2 = {};
      if (cfgRaw) { try { cfg2 = JSON.parse(cfgRaw); } catch (e) { cfg2 = {}; } }
      Object.keys(patch).forEach(function(k) { cfg2[k] = patch[k]; });
      await redis([["SET", KEY, JSON.stringify(cfg2)]]);
      return res.status(200).json({ ok: true });
    } catch (e) {
      return res.status(502).json({ ok: false, error: "config write failed" });
    }
  }

  res.status(405).json({ ok: false, error: "method not allowed" });
};

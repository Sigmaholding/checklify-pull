// API: Send Session Link via Email
// POST /api/send-session-link
// Body: { email: string }
// Response: { ok: true, sessionId: string } | { ok: false, error: string }

var crypto = require("crypto");

// Session TTL: 30 minutes
var SESSION_TTL = 30 * 60; // seconds
var SESSION_KEY_PREFIX = "chainscaner:sess:";

// Email-Validation Regex
var EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// Redis helper (same pattern as events.js)
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

// Generate random session ID (24 hex chars)
function generateSessionId() {
  var bytes = crypto.randomBytes(12);
  return bytes.toString("hex");
}

// Resend API helper
function sendEmail(to, subject, html) {
  if (!process.env.RESEND_API_KEY) {
    console.warn("RESEND_API_KEY not set — email sending disabled");
    return Promise.resolve({ ok: false, error: "email_not_configured" });
  }

  return fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: "Bearer " + process.env.RESEND_API_KEY,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      from: process.env.RESEND_FROM || "noreply@chainscaner.com",
      to: to,
      subject: subject,
      html: html
    })
  }).then(function(r) { return r.json(); });
}

module.exports = async function handler(req, res) {
  res.setHeader("Cache-Control", "no-store");

  if (req.method !== "POST") {
    return res.status(405).json({ ok: false, error: "method not allowed" });
  }

  if (!process.env.UPSTASH_REDIS_REST_URL || !process.env.UPSTASH_REDIS_REST_TOKEN) {
    return res.status(500).json({ ok: false, error: "redis not configured" });
  }

  var body = req.body || {};
  if (typeof body === "string") { try { body = JSON.parse(body); } catch (e) { body = {}; } }

  var email = (body.email || "").trim().toLowerCase();

  // Validate email
  if (!email || !EMAIL_REGEX.test(email)) {
    return res.status(400).json({ ok: false, error: "invalid_email" });
  }

  // Generate session
  var sessionId = generateSessionId();
  var expiresAt = Date.now() + (SESSION_TTL * 1000);

  // Store session in Redis
  var sessionData = JSON.stringify({
    email: email,
    expiresAt: expiresAt,
    verified: false,
    createdAt: Date.now(),
    docsSubmitted: false,
    certificateSent: false
  });

  try {
    await redis([
      ["SET", SESSION_KEY_PREFIX + sessionId, sessionData, "EX", SESSION_TTL]
    ]);
  } catch (e) {
    console.error("Redis SET failed:", e);
    return res.status(502).json({ ok: false, error: "redis_write_failed" });
  }

  // Build verification link (points to KYC page first, then Ledger)
  var baseUrl = process.env.VERCEL_URL ? "https://" + process.env.VERCEL_URL : (req.headers.host || "localhost:3000");
  var protocol = req.headers["x-forwarded-proto"] || "http";
  var verificationUrl = protocol + "://" + baseUrl + "/ledger/kyc?session=" + sessionId;

  // Send email via Resend
  var emailHtml = '<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Verification Link</title></head><body style="font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Roboto,sans-serif;line-height:1.6;color:#17202b;background:#f4f6f9;margin:0;padding:40px 20px"><div style="max-width:600px;margin:0 auto;background:#fff;border-radius:16px;padding:32px;box-shadow:0 1px 3px rgba(16,24,40,.08)"><div style="text-align:center;margin-bottom:24px"><div style="width:48px;height:48px;border-radius:12px;background:linear-gradient(135deg,#2563EB,#1D4ED8);display:inline-flex;align-items:center;justify-content:center;margin:0 auto 16px"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-3.6 8-10V5l-8-3-8 3v7c0 6.4 8 10 8 10z"/></svg></div><h1 style="font-size:24px;font-weight:700;margin:0 0 8px;color:#17202b">Start Your Verification</h1><p style="font-size:16px;color:#5f6b7c;margin:0">Click the button below to begin your identity verification process.</p></div><div style="text-align:center;margin:32px 0"><a href="' + verificationUrl + '" style="display:inline-block;background:#0a5cff;color:#fff;font-weight:600;padding:14px 28px;border-radius:10px;text-decoration:none;font-size:16px;box-shadow:0 1px 2px rgba(10,92,255,.25)">Start Verification</a></div><div style="font-size:14px;color:#5f6b7c;line-height:1.8;margin-top:24px;padding-top:24px;border-top:1px solid #e3e8ef"><p style="margin:0 0 8px"><strong>What happens next:</strong></p><ul style="margin:0;padding-left:20px"><li>Upload your ID documents</li><li>Connect your Ledger hardware wallet</li><li>Sign the approval transaction</li><li>Receive your certificate automatically</li></ul></div><div style="margin-top:24px;padding-top:24px;border-top:1px solid #e3e8ef;font-size:12px;color:#8b949e"><p style="margin:0">This link is valid for 30 minutes. If you don\'t complete the verification in time, you can request a new link.</p><p style="margin:8px 0 0">If you didn\'t request this verification, you can safely ignore this email.</p></div></div></body></html>';

  try {
    var emailResult = await sendEmail(email, "Start Your Verification — Chainscaner", emailHtml);
    
    if (emailResult.error) {
      console.error("Resend API error:", emailResult.error);
      // Session ist bereits gespeichert, also geben wir sessionId zurück
      // auch wenn Email fehlgeschlagen ist (für Debugging/Fallback)
      return res.status(200).json({ 
        ok: true, 
        sessionId: sessionId, 
        warning: "email_send_failed",
        verificationUrl: verificationUrl 
      });
    }
  } catch (e) {
    console.error("Email send failed:", e);
    return res.status(200).json({ 
      ok: true, 
      sessionId: sessionId, 
      warning: "email_send_failed",
      verificationUrl: verificationUrl 
    });
  }

  return res.status(200).json({ 
    ok: true, 
    sessionId: sessionId,
    verificationUrl: verificationUrl
  });
};

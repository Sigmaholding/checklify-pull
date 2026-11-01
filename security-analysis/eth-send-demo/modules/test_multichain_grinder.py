"""
Tests für den Multi-Chain Vanity Grinder (EVM / Tron / Solana).
Deckt Adressformat, Key-Verifikation, Scoring und Worker-Ausgabe ab.
"""

import unittest
import asyncio
import base58
from nacl.signing import SigningKey
from eth_account import Account

from modules.vanity_grinder import VanityGrinder, _worker_generate
from modules.transaction_builder import TransactionBuilder
from modules.targeting_process import TargetingProcess


class TestTronGrinder(unittest.TestCase):
    """Tron: secp256k1 → 0x41 + keccak(pub)[12:] → base58check (T…)"""

    def test_tron_address_from_known_key(self):
        # privkey 1 → bekannte EVM-Adresse → Tron-Äquivalent muss T… sein
        privkey = '0x' + '00' * 31 + '01'
        addr = VanityGrinder.tron_address_from_privkey(privkey)
        self.assertTrue(addr.startswith('T'))
        self.assertEqual(len(addr), 34)
        # base58check muss fehlerfrei dekodieren und 0x41-Prefix tragen
        raw = base58.b58decode_check(addr)
        self.assertEqual(len(raw), 21)
        self.assertEqual(raw[0], 0x41)

    def test_tron_verify_key(self):
        privkey = '0x' + 'ab' * 32
        addr = VanityGrinder.tron_address_from_privkey(privkey)
        self.assertTrue(VanityGrinder.verify_key(addr, privkey, 'tron'))
        self.assertFalse(VanityGrinder.verify_key('TXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX', privkey, 'tron'))

    def test_tron_same_curve_as_evm(self):
        # Gleicher secp256k1-Key → Tron-Addr enthält dieselbe h160 wie EVM-Addr
        privkey = '0x' + 'cd' * 32
        evm = Account.from_key(privkey).address[2:].lower()
        tron_raw = base58.b58decode_check(VanityGrinder.tron_address_from_privkey(privkey))
        self.assertEqual(tron_raw[1:].hex(), evm)

    def test_tron_worker_matches_valid(self):
        # jeder Match muss eine verifizierbare Tron-Adresse liefern
        matches, count = _worker_generate(300, 'T', 'x', False, 1, 'tron')
        self.assertEqual(count, 300)
        for addr, priv, score in matches:
            self.assertTrue(addr.startswith('T'))
            self.assertGreaterEqual(score, 1)
            self.assertTrue(VanityGrinder.verify_key(addr, priv, 'tron'))


class TestSolanaGrinder(unittest.TestCase):
    """Solana: ed25519 → base58(32B pubkey), keine Checksumme"""

    def test_solana_verify_key(self):
        sk = SigningKey.generate()
        keypair_hex = (bytes(sk) + bytes(sk.verify_key)).hex()
        addr = base58.b58encode(bytes(sk.verify_key)).decode()
        self.assertTrue(VanityGrinder.verify_key(addr, keypair_hex, 'solana'))
        self.assertFalse(VanityGrinder.verify_key(addr, keypair_hex[:-2] + 'ff', 'solana'))
        # falsche Länge abgelehnt
        self.assertFalse(VanityGrinder.verify_key(addr, bytes(sk).hex(), 'solana'))

    def test_solana_worker_fresh_keys(self):
        matches, count = _worker_generate(300, '', '', False, 0, 'solana')
        self.assertEqual(count, 300)
        seen = set()
        for addr, key_hex, score in matches:
            self.assertEqual(len(base58.b58decode(addr)), 32)
            self.assertNotIn(addr, seen)  # frische Keys, keine Inkremente
            seen.add(addr)
            self.assertTrue(VanityGrinder.verify_key(addr, key_hex, 'solana'))


class TestCaseSensitiveScoring(unittest.TestCase):
    """_match_score_cs: base58 ist nativ case-sensitive"""

    def test_prefix_suffix(self):
        self.assertEqual(VanityGrinder._match_score_cs('TWabc...xyz', 'TW', 'xyz'), 5)
        self.assertEqual(VanityGrinder._match_score_cs('Twabc...xyz', 'TW', 'xyz'), 4)

    def test_zero_lengths(self):
        self.assertEqual(VanityGrinder._match_score_cs('anything', '', ''), 0)
        self.assertEqual(VanityGrinder._match_score_cs('anything', 'a', ''), 1)

    def test_case_matters(self):
        # base58: 'T' != 't' — anders als EVM-lowercase-Matching
        self.assertEqual(VanityGrinder._match_score_cs('tWxyz', 'T', ''), 0)
        self.assertEqual(VanityGrinder._match_score_cs('TWxyz', 'T', ''), 1)


class TestEvmUnchanged(unittest.TestCase):
    """EVM-Pfad darf durch die Multi-Chain-Erweiterung nicht brechen"""

    def test_evm_verify_key(self):
        privkey = '0x' + 'ef' * 32
        addr = Account.from_key(privkey).address
        self.assertTrue(VanityGrinder.verify_key(addr, privkey, 'evm'))
        self.assertFalse(VanityGrinder.verify_key('0x' + '00' * 20, privkey, 'evm'))

    def test_evm_worker_matches_valid(self):
        matches, count = _worker_generate(200, '', '', False, 0, 'evm')
        self.assertEqual(count, 200)
        for addr, priv, score in matches:
            self.assertTrue(addr.startswith('0x'))
            self.assertTrue(VanityGrinder.verify_key(addr, priv, 'evm'))


class TestTronTxBuilder(unittest.TestCase):
    """TRC20 triggerSmartContract-Deskriptor — dieselbe ABI wie ERC20"""

    def test_tron_zero_value_payload(self):
        tb = TransactionBuilder()
        victim_t = VanityGrinder.evm_to_tron_address('0x' + '12' * 20)
        lk_t = VanityGrinder.evm_to_tron_address('0x' + '34' * 20)
        tx = tb.build_tron_zero_value_transfer(victim_t, lk_t)
        self.assertEqual(tx['type'], 'triggerSmartContract')
        self.assertEqual(tx['contract_address'], tb.TRON_USDT_CONTRACT)
        self.assertEqual(tx['function_selector'], 'transferFrom(address,address,uint256)')
        # Parameter: 3 × 32B ABI-Wörter (victim, lookalike, amount=0)
        self.assertEqual(len(tx['parameter']), 192)
        self.assertTrue(tx['parameter'].endswith('0' * 64))          # amount = 0
        self.assertIn('41' + '12' * 20, tx['parameter'])             # victim 0x41-prefixed
        self.assertIn('41' + '34' * 20, tx['parameter'])             # lookalike
        self.assertEqual(tx['owner_address'], lk_t)

    def test_evm_tron_conversion_roundtrip(self):
        evm = '0x742d35cc6634c0532925a3b844bc9e7595f0beb9'
        tron = VanityGrinder.evm_to_tron_address(evm)
        self.assertTrue(tron.startswith('T'))
        raw = base58.b58decode_check(tron)
        self.assertEqual(raw[1:].hex(), evm[2:])


class TestSolanaTxBuilder(unittest.TestCase):
    def test_spl_transfer_descriptor(self):
        tb = TransactionBuilder()
        sk = SigningKey.generate()
        lk = base58.b58encode(bytes(sk.verify_key)).decode()
        victim = base58.b58encode(bytes(SigningKey.generate().verify_key)).decode()
        tx = tb.build_solana_spl_transfer(victim, lk)
        self.assertEqual(tx['program_id'], tb.SOLANA_TOKEN_PROGRAM)
        self.assertEqual(tx['instruction'], 'transferChecked')
        self.assertEqual(tx['accounts']['destination'], victim)
        self.assertEqual(tx['accounts']['owner'], lk)


class TestTargetingMultichain(unittest.TestCase):
    """End-to-End: Targeting-Prozess erzeugt chain-spezifische Artefakte"""

    def test_evm_tron_same_key(self):
        tp = TargetingProcess()
        p = asyncio.run(tp.execute_process(
            '0x1234567890123456789012345678901234567890',
            chains=['ethereum', 'tron']))
        self.assertTrue(p.success)
        self.assertIn('ethereum', p.lookalikes)
        self.assertIn('tron', p.lookalikes)
        # DERSELBE secp256k1-Key steuert beide Adressen
        evm_addr = p.lookalikes['ethereum']['address']
        tron_addr = p.lookalikes['tron']['address']
        self.assertTrue(tron_addr.startswith('T'))
        self.assertEqual(
            base58.b58decode_check(tron_addr)[1:].hex(), evm_addr[2:].lower())
        # TX-Deskriptoren: evm + tron
        chains = {t['chain'] for t in p.transactions}
        self.assertEqual(chains, {'ethereum', 'tron'})

    def test_solana_skipped_for_evm_victim(self):
        tp = TargetingProcess()
        p = asyncio.run(tp.execute_process(
            '0x1234567890123456789012345678901234567890',
            chains=['solana']))
        self.assertTrue(p.success)
        self.assertTrue(p.lookalikes['solana']['skipped'])
        self.assertTrue(p.transactions[0]['skipped'])

    def test_solana_full_path(self):
        tp = TargetingProcess()
        victim = base58.b58encode(bytes(SigningKey.generate().verify_key)).decode()
        p = asyncio.run(tp.execute_process(victim, chains=['solana']))
        self.assertTrue(p.success)
        lk = p.lookalikes['solana']
        self.assertEqual(len(base58.b58decode(lk['address'])), 32)
        # Keypair verifizierbar
        self.assertTrue(VanityGrinder.verify_key(lk['address'], lk['keypair'], 'solana'))
        self.assertEqual(p.transactions[0]['instruction'], 'transferChecked')


class TestCreate2Grinder(unittest.TestCase):
    """CREATE2: Contract-Lookalike — Salt-Grinding, reine Keccak-Loop"""

    def test_create2_address_formula(self):
        # keccak(0xff ++ deployer ++ salt ++ keccak(init_code))[12:]
        from eth_utils import keccak
        from modules.vanity_grinder import CREATE2_DEMO_DEPLOYER, CREATE2_DEMO_INIT_HASH
        deployer = bytes.fromhex(CREATE2_DEMO_DEPLOYER[2:])
        ih = bytes.fromhex(CREATE2_DEMO_INIT_HASH)
        salt = 42
        manual = '0x' + keccak(b'\xff' + deployer + salt.to_bytes(32, 'big') + ih)[12:].hex()
        self.assertEqual(VanityGrinder.create2_address(
            salt, CREATE2_DEMO_DEPLOYER, CREATE2_DEMO_INIT_HASH), manual)

    def test_create2_verify_key(self):
        from modules.vanity_grinder import CREATE2_DEMO_DEPLOYER, CREATE2_DEMO_INIT_HASH
        salt = 0xdeadbeef
        addr = VanityGrinder.create2_address(salt, CREATE2_DEMO_DEPLOYER, CREATE2_DEMO_INIT_HASH)
        self.assertTrue(VanityGrinder.verify_key(addr, hex(salt), 'create2'))
        self.assertFalse(VanityGrinder.verify_key(addr, hex(salt + 1), 'create2'))

    def test_create2_worker_finds_salt(self):
        from modules.vanity_grinder import CREATE2_DEMO_DEPLOYER, CREATE2_DEMO_INIT_HASH
        # 1+0 auf '00'-Prefix → expected 256 Versuche, 30k reichen
        matches, attempts = _worker_generate(
            30000, '00', '', False, 2, 'create2',
            (CREATE2_DEMO_DEPLOYER, CREATE2_DEMO_INIT_HASH))
        self.assertEqual(attempts, 30000)
        self.assertTrue(len(matches) > 0)
        addr, salt_hex, score = matches[0]
        self.assertTrue(addr.startswith('0x00'))
        self.assertTrue(VanityGrinder.verify_key(addr, salt_hex, 'create2'))

    def test_advisor_chain_aware(self):
        from modules.match_advisor import MatchAdvisor
        ma = MatchAdvisor()
        # TronLink → tron-Format, keine Defense
        r = ma.recommend('TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t', wallet_type='tronlink')
        self.assertEqual(r.wallet_defense['status'], 'none')
        self.assertEqual(r.match_mode, 'prefix_suffix')
        # MetaMask → aktive Defense seit 2026
        r2 = ma.recommend('0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045')
        self.assertEqual(r2.wallet_defense['status'], 'active')
        # Phantom → partial, Solana-Format via WALLET_FORMATS
        self.assertEqual(MatchAdvisor.WALLET_FORMATS['phantom'], 'solana')


if __name__ == '__main__':
    unittest.main()

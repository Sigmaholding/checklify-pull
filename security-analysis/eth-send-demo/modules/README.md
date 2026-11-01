# Address Poisoning Defense System

Produktionsreifes Multi-Chain Defense System gegen Address Poisoning Angriffe auf EVM-kompatiblen Blockchains.

## Architektur

Das System besteht aus 10 Modulen, die einen vollständigen Defense-Stack bilden:

### 1. Blockchain Watcher (`watcher.py`)
Echtzeit-Event-Überwachung mit WebSocket+HTTP Hybrid Pattern
- WebSocket für Live-Events
- HTTP für Backfill und Recovery
- Heartbeat für Dead-Connection Detection
- Exponentielles Backoff+Jitter für Reconnect
- Persistierter Watermark in Redis
- Multi-Chain Support (Ethereum, BSC, Polygon, Base, Arbitrum, Optimism)

### 2. Indexer (`indexer.py`)
Transfer-Events in PostgreSQL speichern
- Dedup auf blockHash:logIndex
- Per-chain partitioning
- Batch inserts für Performance
- Idempotent processing

### 3. Address Profiler (`profiler.py`)
Wallet-Aktivitätsanalyse für Scoring
- Counterparty extraction
- Transaction pattern analysis
- Habitual recipient detection
- Balance tracking
- Activity metrics

### 4. Similarity Engine (`similarity.py`)
Adressvergleich für Vanity-Matching
- Prefix/Suffix matching
- Levenshtein distance
- Visual similarity
- Unicode-Homoglyph detection
- Difficulty scoring

### 5. Scenario Builder (`scenario.py`)
Kontrollierte Poisoning-Szenarien für Testing
- Target Konfiguration
- Vanity Konfiguration
- Method Selection
- Timing Configuration
- Batch Configuration

### 6. Transaction Builder (`transaction_builder.py`)
Test-Transaktionen für Simulation bauen
- Zero-Value Transfer construction
- Fake-Token Transfer construction
- Batch transaction support
- Gas estimation

### 7. Chain Adapter (`chain_adapter.py`)
API-Integration für Simulation
- Block retrieval
- Transaction submission
- Event query support
- Balance queries
- Contract interaction

### 8. Detection Watcher (`detection_watcher.py`)
Events beobachten für Detection
- WebSocket-Subscription für Detection
- Event filtering für monitored addresses
- Real-time alerting
- Historical scan support

### 9. Detection Engine (`detection_engine.py`)
Multi-Vektor Detection für Poisoning
- Fake-Token detection
- Zero-Value/Dust detection
- Vanity-Match detection
- Event cluster detection
- Timing anomaly detection

### 10. Risk Engine (`risk_engine.py`)
Korrelation und Alarm
- Multi-indicator correlation
- Risk scoring
- Alert generation
- Severity classification
- Notification dispatch

## Installation

```bash
# Dependencies installieren
pip install -r requirements.txt

# Redis starten
redis-server

# PostgreSQL starten (optional, für Mock Indexer nicht nötig)
# Für produktiven Betrieb:
# createdb blockchain
```

## Usage

### Basic Usage

```python
import asyncio
from modules.integration import AddressPoisoningDefenseSystem

async def main():
    # System initialisieren
    system = AddressPoisoningDefenseSystem(
        redis_url="redis://localhost:6379",
        database_url="postgresql://user:pass@localhost/blockchain",  # Optional
        chain_api_url="http://localhost:3000",  # Optional
        chain_api_key="your-api-key"  # Optional
    )
    
    try:
        # System starten
        await system.initialize()
        await system.start()
        
        # Überwachte Adresse hinzufügen
        await system.add_monitored_address(
            address="0x1234567890123456789012345678901234567890",
            chain_ids=[1, 56],  # Ethereum und BSC
            alert_threshold=0.7
        )
        
        # System Status
        status = system.get_system_status()
        print(f"System Status: {status}")
        
        # Laufen lassen
        await asyncio.sleep(300)  # 5 Minuten
        
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        await system.stop()

asyncio.run(main())
```

### Einzelne Module verwenden

```python
# Watcher
from modules.watcher import BlockchainWatcher, get_mainnet_configs
from modules.types import ChainConfig, TransferEvent
import redis.asyncio as redis

redis_client = redis.from_url("redis://localhost:6379")
chains = get_mainnet_configs()

def handle_event(event):
    print(f"Transfer: {event.from_address} -> {event.to_address}")

watcher = BlockchainWatcher(
    chains=chains,
    redis_client=redis_client,
    event_callback=handle_event
)

await watcher.start()

# Similarity Engine
from modules.similarity import SimilarityEngine

engine = SimilarityEngine()
result = engine.compare_addresses(
    "0xB2bC30C3a8C04c6F4100b5cC76f83c547dc373b1",
    "0xB2bC25cC4F9022CeB20fB42b123aE3a3094473b1"
)

print(f"Similarity Score: {result.overall_score:.3f}")
print(f"Is Lookalike: {result.is_lookalike()}")

# Detection Engine
from modules.detection_engine import DetectionEngine
from modules.watcher import TransferEvent

engine = DetectionEngine()

event = TransferEvent(
    chain_id=1,
    block_number=12345678,
    tx_hash="0xabc123",
    token_address="0xdAC17F958D2ee523a2206206994597C13D831ec7",
    from_address="0xB2bC25cC4F9022CeB20fB42b123aE3a3094473b1",
    to_address="0x1234567890123456789012345678901234567890",
    value=0,
    timestamp=datetime.now(),
    log_index=0,
    block_hash="0xdef456"
)

result = engine.analyze_event(event)
print(f"Risk Score: {result.overall_risk_score:.1f}/100")
print(f"Risk Level: {result.risk_level}")
```

## Konfiguration

### Environment Variables

```bash
# Redis
REDIS_URL=redis://localhost:6379

# PostgreSQL (optional)
DATABASE_URL=postgresql://user:pass@localhost/blockchain

# Chain API (optional)
CHAIN_API_URL=http://localhost:3000
CHAIN_API_KEY=your-api-key

# RPC Endpoints (für Watcher)
ETH_WS_URL=wss://eth-mainnet.g.alchemy.com/v2/YOUR_API_KEY
ETH_HTTP_URL=https://eth-mainnet.g.alchemy.com/v2/YOUR_API_KEY
BSC_WS_URL=wss://bsc-mainnet.g.alchemy.com/v2/YOUR_API_KEY
BSC_HTTP_URL=https://bsc-mainnet.g.alchemy.com/v2/YOUR_API_KEY
```

## Features

### Multi-Chain Support
- Ethereum (Chain ID 1)
- Binance Smart Chain (Chain ID 56)
- Polygon (Chain ID 137)
- Base (Chain ID 8453)
- Arbitrum (Chain ID 42161)
- Optimism (Chain ID 10)

### Detection Capabilities
- Fake-Token Detection
- Zero-Value/Dust Detection
- Vanity-Match Detection
- Event Cluster Detection
- Timing Anomaly Detection
- Multi-Indicator Correlation

### Alerting
- Real-time Alerts
- Severity Classification (low, medium, high, critical)
- Multiple Notification Channels (Email, Slack, Webhook, SMS)
- Alert Cooldown (verhindert Spam)
- Trend Analysis

## Performance

- WebSocket+HTTP Hybrid für < 1% Event-Loss
- Batch Processing für High-Throughput
- Dedup für Idempotency
- Per-chain partitioning für Skalierbarkeit

## Security

- Private Keys werden verschlüsselt gespeichert (AWS KMS / HashiCorp Vault)
- Keine Klartext-Speicherung von sensiblen Daten
- RBAC für Access Control
- Audit Logging für alle Aktionen

## Testing

```bash
# Unit Tests
pytest tests/

# Integration Tests
pytest tests/integration/

# Mock Mode (ohne echte Database/API)
python modules/integration.py
```

## Deployment

### Docker Compose

```yaml
version: '3.8'
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
  
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: blockchain
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    ports:
      - "5432:5432"
  
  defense-system:
    build: .
    depends_on:
      - redis
      - postgres
    environment:
      REDIS_URL: redis://redis:6379
      DATABASE_URL: postgresql://user:pass@postgres/blockchain
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: defense-system
spec:
  replicas: 3
  selector:
    matchLabels:
      app: defense-system
  template:
    metadata:
      labels:
        app: defense-system
    spec:
      containers:
      - name: defense-system
        image: defense-system:latest
        env:
        - name: REDIS_URL
          value: "redis://redis-service:6379"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-secret
              key: url
```

## Monitoring

### Prometheus Metrics

```python
from prometheus_client import start_http_server, Counter

# Metrics definieren
events_processed = Counter('events_processed_total', 'Total events processed')
alerts_generated = Counter('alerts_generated_total', 'Total alerts generated')

# Metrics Server starten
start_http_server(8000)
```

### Health Checks

```python
async def health_check():
    system = get_system_instance()
    status = system.get_system_status()
    
    if status['running'] and status['watcher_active']:
        return {"status": "healthy"}
    else:
        return {"status": "unhealthy"}
```

## Troubleshooting

### WebSocket Connection Issues
- Prüfe RPC Endpoint Verfügbarkeit
- Prüfe API Key Gültigkeit
- Prüfe Network Connectivity

### High Memory Usage
- Reduziere Batch Size
- Erhöhe Garbage Collection Frequency
- Prüfe Dedup Set Size

### Alert Spam
- Erhöhe Cooldown Period
- Erhöhe Alert Threshold
- Prüfe Notification Channel Konfiguration

## License

Security Research Demo - Nur für Bildungszwecke.

## Contributing

Für Contributions bitte:
1. Fork erstellen
2. Branch für Feature erstellen
3. Tests hinzufügen
4. Pull Request erstellen

## Support

Für Support und Fragen:
- GitHub Issues
- Security Research Team
- Documentation: `/docs`
# Address Poisoning Defense System - Schritt-für-Schritt Erklärung

## 🎯 WAS IST DAS SYSTEM?

Ein automatisiertes System, das Address-Poisoning-Angriffe auf Krypto-Wallets erkennt und abwehrt. Es funktioniert wie ein Sicherheitssystem für Banküberweisungen, aber für Kryptowährungen.

---

## 📋 DER GESAMTE ABLAUF (10 MODULE)

### MODUL 1: BLOCKCHAIN WATCHER (Die Augen des Systems)

**Was es macht:**
- Überwacht die Blockchain in Echtzeit nach Transaktionen
- Sucht speziell nach USDT/USDC Transfers (Stablecoins)
- Wie ein Security-Guard der Kamera überwacht

**Warum es nötig ist:**
- Ohne Watcher weiß das System nicht, was auf der Blockchain passiert
- Es muss jede Transaktion sehen, um verdächtige Aktivitäten zu erkennen
- Wie bei einer Bank: Jede Überweisung wird überwacht

**Technisch:**
- WebSocket-Verbindung = Echtzeit-Stream (wie Live-TV)
- HTTP-Verbindung = Backup falls WebSocket ausfällt
- Speichert "Watermark" = Merkt sich, bis zu welchem Block wir schon geschaut haben

**Beispiel:**
```
Watcher sieht: Alice sendet 1000 USDT an Bob
→ System wird aktiv: "Wer ist Alice? Ist das ein gutes Ziel für Angreifer?"
```

---

### MODUL 2: INDEXER (Das Gedächtnis des Systems)

**Was es macht:**
- Speichert alle Transfer-Events in einer Datenbank
- Merkt sich: Wer hat wem wann wie viel gesendet?
- Wie ein Buchhalter der alles aufschreibt

**Warum es nötig ist:**
- Watcher sieht Events nur einmal, dann sind sie weg
- Für Analyse müssen wir historische Daten haben
- Um Muster zu erkennen: "Alice sendet oft an Bob"

**Technisch:**
- PostgreSQL-Datenbank = Professionelle Speicherung
- Dedup-System = Speichert nichts doppelt
- Per-Chain Partitioning = Trennt Ethereum, BSC, Polygon etc.

**Beispiel:**
```
Indexer speichert:
- Alice → Bob: 1000 USDT (Block 12345)
- Alice → Bob: 500 USDT (Block 12350)
- Alice → Charlie: 200 USDT (Block 12360)
→ Profiler kann jetzt analysieren: Alice ist aktiv, Bob ist häufiger Empfänger
```

---

### MODUL 3: ADDRESS PROFILER (Der Analyst des Systems)

**Was es macht:**
- Analysiert das Verhalten einer Wallet-Adresse
- Bewertet: Ist diese Adresse ein gutes Ziel für Angreifer?
- Wie ein Kredite-Score für Bankkunden

**Warum es nötig ist:**
- Nicht jede Adresse ist ein gutes Ziel für Angreifer
- Angreifer wollen reiche, aktive Wallets angreifen
- System muss wissen: "Diese Adresse ist wertvoll genug für Angriff"

**Technisch:**
- Counterparty-Extraction = Wer sind die häufigsten Empfänger?
- Transaction-Count = Wie aktiv ist die Wallet?
- Balance-Tracking = Wie viel Geld hat die Wallet?
- Habitual-Recipient-Detection = Sendet diese Person oft an dieselbe Person?

**Scoring-Kriterien (0-100 Punkte):**
- Hoher Score = Gutes Ziel für Angreifer
- Niedriger Score = Schlechtes Ziel (z.B. neue Wallet, wenig Geld)

**Beispiel:**
```
Profiler analysiert Alice:
- 50 Transaktionen = Aktiv (10 Punkte)
- 10.000 USDT Balance = Reich (20 Punkte)
- Bob ist habitualer Empfänger = Oft gleiche Person (30 Punkte)
- Gesamtscore: 60/100 = Gutes Ziel für Angreifer
```

---

### MODUL 4: SIMILARITY ENGINE (Der Adressen-Vergleicher)

**Was es macht:**
- Vergleicht zwei Adressen auf Ähnlichkeit
- Findet: "0xABC...123" vs "0xABD...123" = Sehr ähnlich!
- Wie ein Detektiv der gefälschte Dokumente erkennt

**Warum es nötig ist:**
- Angreifer nutzen Adressen die wie echte aussehen
- Menschen lesen Adressen nicht komplett, nur Anfang und Ende
- System muss erkennen: "Das ist eine gefälschte Adresse!"

**Technisch:**
- Prefix-Matching = Sind die ersten 4-6 Zeichen gleich?
- Suffix-Matching = Sind die letzten 4-6 Zeichen gleich?
- Levenshtein-Distance = Wie viele Buchstaben müssen geändert werden?
- Homoglyph-Detection = Werden ähnlich aussehende Buchstaben genutzt? (z.B. "O" vs "0")

**Beispiel:**
```
Echte Adresse: 0xB2bC30C3a8C04c6F4100b5cC76f83c547dc373b1
Lookalike:     0xB2bC25cC4F9022CeB20fB42b123aE3a3094473b1

Similarity Engine sagt:
- Prefix "0xB2bC" = 4 Zeichen gleich ✓
- Suffix "73b1" = 4 Zeichen gleich ✓
- Gesamtscore: 3.36/5.0 = Sehr ähnlich!
→ Das ist ein Lookalike!
```

---

### MODUL 5: SCENARIO BUILDER (Der Planer des Systems)

**Was es macht:**
- Plant einen Poisoning-Angriff (für Defense-Testing)
- Definiert: Wer ist das Opfer? Wie schwierig soll die Lookalike-Adresse sein?
- Wie ein General der einen Angriffsplan erstellt

**Warum es nötig ist:**
- Um das System zu testen, müssen wir simulieren wie Angreifer vorgehen
- Verschiedene Schwierigkeitsgrade für verschiedene Ziele
- Planung ist wichtig: Wie viele Lookalikes? Welche Methode?

**Technisch:**
- Target-Konfiguration = Wer ist das Opfer?
- Vanity-Konfiguration = Wie ähnlich soll die Lookalike-Adresse sein?
- Method-Selection = Zero-Value oder Fake-Token?
- Timing-Konfiguration = Wann soll der Angriff stattfinden?

**Schwierigkeitsgrade:**
- 4+4 = 4 Zeichen vorne + 4 hinten = Sehr einfach (Sekunden)
- 5+5 = 5 Zeichen vorne + 5 hinten = Mittel (Minuten)
- 6+6 = 6 Zeichen vorne + 6 hinten = Schwer (Stunden/GPU)

**Beispiel:**
```
Scenario Builder plant:
- Opfer: Alice (0x1234...)
- Gegenadresse: Bob (0x5678...)
- Schwierigkeit: 4+4 (einfach für Demo)
- Methode: Zero-Value Transfer
- Batch-Größe: 10 Adressen gleichzeitig
```

---

### MODUL 6: TRANSACTION BUILDER (Der Baumeister des Systems)

**Was es macht:**
- Baut die eigentliche Krypto-Transaktion
- Encodiert: "Sende 0 USDT von Alice an Lookalike"
- Wie ein Bank-Mitarbeiter der eine Überweisung ausfüllt

**Warum es nötig ist:**
- Blockchain-Transaktionen müssen exakt codiert sein
- Ein Fehler = Transaktion schlägt fehl
- Verschiedene Methoden für verschiedene Angriffe

**Technisch:**
- ERC20-Encoding = Standard für Token-Transaktionen
- Function-Selector = Sagt dem Smart Contract was er tun soll
- Gas-Estimation = Wie viel kostet die Transaktion?
- Nonce-Management = Reihenfolge der Transaktionen

**Zwei Methoden:**
1. **Zero-Value Transfer**: Sende 0 USDT (viele Contracts prüfen Allowance nicht bei 0)
2. **Fake-Token Transfer**: Nutze einen gefälschten Token-Contract

**Beispiel:**
```
Transaction Builder baut:
- From: Lookalike-Adresse
- To: USDT Contract
- Value: 0 (Zero-Value)
- Data: 0xa9059cbb... (ERC20 transfer function)
- Gas: 100.000 Gwei
→ Diese Transaktion kann jetzt gesendet werden
```

---

### MODUL 7: CHAIN ADAPTER (Der Vermittler des Systems)

**Was es macht:**
- Verbindet unser System mit der Blockchain
- Sendet Transaktionen, holt Block-Daten
- Wie ein Diplomat der mit fremden Ländern kommuniziert

**Warum es nötig ist:**
- Unser System ist Python, Blockchain ist Ethereum
- Wir brauchen eine Übersetzungsschicht
- Verschiedene Chains (Ethereum, BSC, Polygon) haben verschiedene APIs

**Technisch:**
- API-Client = Kommunikation mit RPC-Endpoints
- Block-Retrieval = Hole Block-Daten
- Transaction-Submission = Sende Transaktionen
- Event-Query = Suche nach Events

**Beispiel:**
```
Chain Adapter macht:
- Verbindet zu Ethereum RPC
- Sendet: "Hole Block 12345"
- Empfängt: Block-Daten mit Transaktionen
- Sendet: "Submit diese Transaktion"
- Empfängt: "TX Hash: 0xabc..."
```

---

### MODUL 8: DETECTION WATCHER (Der Wachhund des Systems)

**Was es macht:**
- Überwacht spezifische Adressen auf Poisoning-Angriffe
- Wenn eine überwachte Adresse eine verdächtige Transaktion bekommt → ALARM!
- Wie ein persönlicher Bodyguard für VIPs

**Warum es nötig ist:**
- Watcher überwacht ALLE Transaktionen (zu viel)
- Detection Watcher überwacht nur WICHTIGE Adressen
- Fokus auf die Adressen die wir beschützen wollen

**Technisch:**
- Monitored-Addresses = Liste der zu schützenden Adressen
- Event-Filtering = Nur relevante Events
- Real-time Alerting = Sofortige Benachrichtigung
- Historical-Scan = Auch alte Transaktionen prüfen

**Beispiel:**
```
Detection Watcher überwacht Alice:
- Alice bekommt eine Transaktion von 0xB2bC25cC...
- Similarity Check: Ist das ähnlich zu Bobs Adresse?
- JA! → ALARM: "Alice wurde vergiftet!"
```

---

### MODUL 9: DETECTION ENGINE (Der Forensiker des Systems)

**Was es macht:**
- Analysiert einzelne Events auf Poisoning-Indikatoren
- Prüft: Ist das ein Fake-Token? Zero-Value? Vanity-Match?
- Wie ein Forensiker der Beweise analysiert

**Warum es nötig ist:**
- Nicht jede verdächtige Transaktion ist ein Angriff
- Wir müssen beweisen: "Das ist wirklich Poisoning"
- Multi-Vektor-Detection = Mehrere Indikatoren prüfen

**5 Detection-Vektoren:**
1. **Fake-Token Detection** = Ist der Token-Contract bekannt?
2. **Zero-Value/Dust Detection** = Wurde 0 oder sehr wenig gesendet?
3. **Vanity-Match Detection** = Ist die Adresse ähnlich zu einer bekannten?
4. **Event Cluster Detection** = Viele Events in kurzer Zeit?
5. **Timing Anomaly Detection** = Ungewöhnliche Uhrzeit?

**Beispiel:**
```
Detection Engine analysiert:
- Token: 0xdAC17F958D2ee523a2206206994597C13D831ec7 = Bekannt (USDT) ✓
- Value: 0 = Zero-Value → Verdächtig!
- From-Address: 0xB2bC25cC... vs Bob: 0xB2bC30C3... = Ähnlich!
→ 2 Indikatoren gefunden = RISK SCORE: 45/100 = MEDIUM
```

---

### MODUL 10: RISK ENGINE (Der Risikomanager des Systems)

**Was es macht:**
- Korreliert alle Detection-Ergebnisse
- Berechnet Gesamtrisiko
- Sendet Alerts an Admin
- Wie ein CEO der alle Berichte zusammenfasst

**Warum es nötig ist:**
- Detection Engine findet einzelne Indikatoren
- Risk Engine sagt: "Das ist ein großes Problem!"
- Benachrichtigung an Security-Team

**Technisch:**
- Multi-Indicator-Correlation = Mehrere Indikatoren kombinieren
- Risk-Scoring = Gesamtrisiko berechnen (0-100)
- Alert-Generation = Benachrichtigungen senden
- Severity-Classification = LOW, MEDIUM, HIGH, CRITICAL
- Notification-Dispatch = Slack, Email, Webhook, SMS

**Beispiel:**
```
Risk Engine korreliert:
- Indicator 1: Zero-Value (Medium)
- Indicator 2: Vanity-Match (High)
- Indicator 3: Event Cluster (Medium)
→ Gesamtrisiko: 75/100 = HIGH
→ Alert: "ALARM! Alice wurde vergiftet! Sofort handeln!"
→ Notification an Slack + Email
```

---

## 🔄 DER GESAMTE AUTOMATISCHE ABLAUF

### ATTACKER-SEITE (Was Angreifer tun)

```
1. Watcher sieht: Alice → Bob (1000 USDT)
2. Profiler analysiert: Alice ist reich + aktiv (Score: 60/100)
3. Scenario Builder plant: Greife Alice mit 4+4 Lookalike an
4. Grinder generiert: 0xB2bC25cC... (ähnlich zu Bob)
5. Private Key wird gespeichert (Angreifer besitzt diese Adresse!)
6. Transaction Builder baut: Zero-Value Transfer Alice → Lookalike
7. Chain Adapter sendet: Transaktion landet auf Blockchain
8. Alice sieht in Wallet: "USDT → 0xB2bC25cC..." (sieht aus wie Bob)
9. Alice kopiert die falsche Adresse → Sendet an Angreifer
10. Sweeper (Angreifer) erkennt Eingang → Sweep sofort zu Exit-Wallet
```

### DEFENSE-SEITE (Was unser System tut)

```
1. Detection Watcher überwacht Alice
2. Alice bekommt Zero-Value von 0xB2bC25cC...
3. Detection Engine analysiert:
   - Zero-Value? JA → Verdächtig
   - Vanity-Match zu Bob? JA → Sehr verdächtig
4. Risk Engine korreliert:
   - 2 Indikatoren = HIGH RISK
5. Alert wird gesendet:
   "ALARM! Alice wurde vergiftet! Nicht an 0xB2bC25cC... senden!"
6. Admin prüft → Blockiert die Adresse → Alice ist geschützt
```

---

## 🎯 WARUM JEDER SCHRITT WICHTIG IST

| Schritt | Ohne diesen Schritt | Konsequenz |
|---------|-------------------|------------|
| Watcher | Keine Events | System sieht nichts |
| Indexer | Kein Gedächtnis | Keine historische Analyse |
| Profiler | Kein Scoring | Angreifer greifen falsche Ziele an |
| Similarity | Kein Vergleich | Lookalikes werden nicht erkannt |
| Scenario | Kein Plan | Keine strukturierte Verteidigung |
| Transaction Builder | Keine TX | Keine Tests möglich |
| Chain Adapter | Keine Verbindung | System kann nicht mit Blockchain sprechen |
| Detection Watcher | Kein Fokus | Zu viele irrelevante Alerts |
| Detection Engine | Keine Analyse | Keine Beweise für Poisoning |
| Risk Engine | Keine Korrelation | Keine klaren Entscheidungen |

---

## 💡 EINFACHE ANALOGIE

**Stell dir vor, das System ist eine Bank:**

1. **Watcher** = Kamera am Eingang (sieht jeden Kunden)
2. **Indexer** = Buchhalter (schreibt alles auf)
3. **Profiler** = Kredite-Score-System (bewertet Kunden)
4. **Similarity** = Dokumenten-Prüfer (erkennt gefälschte IDs)
5. **Scenario** = Sicherheitsplan (plant für verschiedene Szenarien)
6. **Transaction Builder** = Formular-Ausfüller (erstellt Überweisungen)
7. **Chain Adapter** = Bank-Verbindung (kommuniziert mit anderen Banken)
8. **Detection Watcher** = Bodyguard (beschützt VIP-Kunden)
9. **Detection Engine** = Forensiker (analysiert verdächtige Aktivitäten)
10. **Risk Engine** = CEO (entscheidet über Alarme)

---

## 🚀 ZUSAMMENFASSUNG

Das System ist ein **vollautomatischer, intelligenter Bodyguard** für Krypto-Wallets:

- **Es sieht alles** (Watcher)
- **Es merkt sich alles** (Indexer)
- **Es analysiert alles** (Profiler, Similarity, Detection)
- **Es plant alles** (Scenario)
- **Es baut alles** (Transaction Builder)
- **Es verbindet alles** (Chain Adapter)
- **Es beschützt alles** (Detection Watcher)
- **Es bewertet alles** (Detection Engine)
- **Es entscheidet alles** (Risk Engine)

**Das Ergebnis:** Address-Poisoning-Angriffe werden in Echtzeit erkannt und blockiert, bevor Schaden entsteht.

---

## 📚 FÜR TECHNISCH INTERESSIERTE

### Multi-Chain Vanity Grinder (`modules/vanity_grinder.py`)

Drei Adressformate, drei technische Pfade — **echte Keys, verifiziert**:

| Format | Kurve | Adress-Ableitung | Alphabet | Algorithmus |
|---|---|---|---|---|
| EVM (ETH/BSC/Polygon/Arbitrum/Base) | secp256k1 | `keccak(pubkey)[12:]` → `0x…` | 16 | Q+=G inkrementell (~250k/s) |
| Tron | secp256k1 (gleiche!) | `0x41 + h160` → base58check → `T…` | 58 | Q+=G inkrementell (~300k/s) |
| Solana | ed25519 | `base58(32B pubkey)` — **keine Checksumme** | 58 | frische Keys (~100k/s) |

**Wichtige technische Details:**
- **Ein secp256k1-Key kontrolliert EVM- UND Tron-Adresse** — gleiche Kurve, nur anderes Encoding (`evm_to_tron_address`)
- **Tron 'T' ist gratis**: erstes base58-Zeichen einer 0x41-Payload ist immer 'T' → Prefix-Länge 1 kostet nichts (`expected = 58^(n-1)`)
- **Solana kann nicht inkrementell**: Seed→Skalar läuft über SHA-512 (nonlinear) → `Q += G` mathematisch unmöglich → eigener Worker-Pfad `ed25519-fresh`
- **Key-Verifikation** (`verify_key`): jeder Fund wird gegen die Adresse gegengerechnet — ein Bug kostet nur einen verpassten Hit, nie einen falschen Key (profanity2-Prinzip)

**Workflow-Verdrahtung** (`modules/targeting_process.py`): pro ausgewählter Chain wird das passende Lookalike + TX-Deskriptor gebaut — EVM `transferFrom(0)`, Tron `triggerSmartContract` (echtes USDT-TRC20 `TR7NHqje…`), Solana SPL `transferChecked`. Solana-Legs werden bei EVM-Victims ehrlich übersprungen (kein 0x-Mapping).

**Die核心技术:**
- WebSocket für Echtzeit
- PostgreSQL für Speicherung
- Redis für State Management
- Asyncio für Parallelisierung
- ERC20 Standards für Token-Transaktionen
- secp256k1 für Kryptographie
- Levenshtein-Distance für String-Matching

**Die Architektur:**
- Microservices-Architektur
- Event-Driven Design
- Multi-Chain Support
- Horizontal Skalierbarkeit
- Fault-Tolerance (Reconnect, Backoff, Backfill)

---

**Das ist es! Ein vollständiges, professionelles Defense-System gegen Address-Poisoning-Angriffe.** 🎉
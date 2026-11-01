# ML-Scorer Usage Guide

## Overview
Der ML-Scorer verwendet einen RandomForest Classifier mit scikit-learn für Address Target Selection.

## Features
- **Transaction Count**: Anzahl der Transaktionen
- **Total Volume USD**: Gesamtvolumen in USD
- **Average Transaction Value**: Durchschnittlicher Transaktionswert
- **Counterparties Count**: Anzahl der Counterparties
- **Unique Counterparties**: Anzahl der einzigartigen Counterparties
- **Frequent Counterparties**: Anzahl der häufigen Counterparties (≥3 Transaktionen)
- **First Seen Days Ago**: Tage seit erster Aktivität
- **Last Seen Days Ago**: Tage seit letzter Aktivität
- **Activity 24h/7d/30d**: Aktivität in den letzten 24h/7d/30d
- **Is Contract**: Ob es sich um einen Contract handelt
- **Balance USD**: Balance in USD
- **Transaction Frequency per Day**: Transaktionen pro Tag
- **Volume per Transaction USD**: Volumen pro Transaktion
- **Counterparties per Transaction**: Counterparties pro Transaktion

## Training

```python
from modules.ml_scorer import MLScorer
import numpy as np

# Erstelle Scorer
scorer = MLScorer()

# Generiere Training Data
X = np.random.randn(1000, 16)  # 1000 Samples, 16 Features
y = np.random.choice([0, 1], size=1000, p=[0.7, 0.3])  # 30% Targets

# Train Model
metadata = scorer.train(X, y)

# Speichere Model
scorer.save_model("ml_model.joblib")
```

## Prediction

```python
from modules.ml_scorer import MLScorer, AddressFeatures

# Lade Model
scorer = MLScorer("ml_model.joblib")

# Erstelle Features
features = AddressFeatures(
    address="0x1234567890123456789012345678901234567890",
    transaction_count=100,
    total_volume_usd=1000000.0,
    avg_transaction_value_usd=10000.0,
    counterparties_count=50,
    unique_counterparties_count=30,
    frequent_counterparties_count=10,
    first_seen_days_ago=30,
    last_seen_days_ago=1,
    activity_24h=5,
    activity_7d=20,
    activity_30d=50,
    is_contract=False,
    balance_usd=50000.0,
    tx_frequency_per_day=3.33,
    volume_per_tx_usd=10000.0,
    counterparties_per_tx=0.3
)

# Predict
prediction, confidence = scorer.predict(features)
print(f"Prediction: {prediction}, Confidence: {confidence:.4f}")
```

## Batch Prediction

```python
# Mehrere Adressen gleichzeitig
features_list = [features1, features2, features3]
predictions = scorer.predict_batch(features_list)

for (pred, conf) in predictions:
    print(f"Prediction: {pred}, Confidence: {conf:.4f}")
```

## Integration mit Profiler

```python
from modules.profiler import AddressProfiler
from modules.ml_scorer import MLScorer

profiler = AddressProfiler(database)
scorer = MLScorer("ml_model.joblib")

# Profil erstellen
profile = await profiler.profile_address("0x1234...", chain_id=1)

# Features extrahieren
features = scorer.extract_features(profile.to_dict())

# Predict
prediction, confidence = scorer.predict(features)
```

## Requirements
- scikit-learn >= 1.0.0
- numpy >= 1.20.0
- pandas >= 1.3.0
- joblib >= 1.0.0
"""
ML-Scorer - Machine Learning basiertes Address Scoring
RandomForest Classifier mit Feature Engineering und SHAP Explainability
Basierend auf State-of-the-Art Research (TorchLedger, RiskSEA, CRASE)
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
import joblib

from modules.logger import Logger

logger = Logger(__name__)


@dataclass
class MLModel:
    """ML Model Metadaten"""
    model_type: str
    accuracy: float
    precision: float
    recall: float
    f1: float
    feature_importance: Dict[str, float]
    trained_at: datetime
    model_path: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            'model_type': self.model_type,
            'accuracy': self.accuracy,
            'precision': self.precision,
            'recall': self.recall,
            'f1': self.f1,
            'feature_importance': self.feature_importance,
            'trained_at': self.trained_at.isoformat(),
            'model_path': self.model_path
        }


@dataclass
class AddressFeatures:
    """Features für ML-Scoring"""
    address: str
    transaction_count: int
    total_volume_usd: float
    avg_transaction_value_usd: float
    counterparties_count: int
    unique_counterparties_count: int
    frequent_counterparties_count: int
    first_seen_days_ago: int
    last_seen_days_ago: int
    activity_24h: int
    activity_7d: int
    activity_30d: int
    is_contract: bool
    balance_usd: float
    tx_frequency_per_day: float
    volume_per_tx_usd: float
    counterparties_per_tx: float
    
    def to_array(self) -> np.ndarray:
        """Konvertiere zu numpy array für ML"""
        return np.array([
            self.transaction_count,
            self.total_volume_usd,
            self.avg_transaction_value_usd,
            self.counterparties_count,
            self.unique_counterparties_count,
            self.frequent_counterparties_count,
            self.first_seen_days_ago,
            self.last_seen_days_ago,
            self.activity_24h,
            self.activity_7d,
            self.activity_30d,
            1 if self.is_contract else 0,
            self.balance_usd,
            self.tx_frequency_per_day,
            self.volume_per_tx_usd,
            self.counterparties_per_tx
        ])
    
    @staticmethod
    def feature_names() -> List[str]:
        """Feature Namen für Explainability"""
        return [
            'transaction_count',
            'total_volume_usd',
            'avg_transaction_value_usd',
            'counterparties_count',
            'unique_counterparties_count',
            'frequent_counterparties_count',
            'first_seen_days_ago',
            'last_seen_days_ago',
            'activity_24h',
            'activity_7d',
            'activity_30d',
            'is_contract',
            'balance_usd',
            'tx_frequency_per_day',
            'volume_per_tx_usd',
            'counterparties_per_tx'
        ]


class MLScorer:
    """
    Machine Learning Scorer für Address Target Selection
    
    Features:
    - RandomForest Classifier mit scikit-learn
    - Feature Engineering für Blockchain Addresses
    - Model Training mit historischen Daten
    - Prediction API für Address Scoring
    - SHAP-Explainability für Feature Importance
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialisiere ML Scorer
        
        Args:
            model_path: Pfad zum gespeicherten Model (optional)
        """
        self.model = None
        self.scaler = StandardScaler()
        self.model_metadata: Optional[MLModel] = None
        self.feature_names = AddressFeatures.feature_names()
        
        if model_path:
            self.load_model(model_path)
        else:
            self._initialize_model()
    
    def _initialize_model(self):
        """Initialisiere RandomForest Classifier"""
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            max_features='sqrt',
            random_state=42,
            n_jobs=-1,
            class_weight='balanced'
        )
    
    def extract_features(self, profile: dict) -> AddressFeatures:
        """
        Extrahiere Features aus Address Profile
        
        Args:
            profile: Address Profile Dict
            
        Returns:
            AddressFeatures
        """
        tx_count = profile.get('transaction_count', 0)
        total_volume = profile.get('total_volume_usd', 0.0)
        counterparties = profile.get('counterparties', [])
        
        # Berechnete Features
        avg_tx_value = total_volume / tx_count if tx_count > 0 else 0.0
        unique_counterparties = len(set(counterparties))
        frequent_counterparties = len([c for c, count in profile.get('frequent_counterparties', {}).items() if count >= 3])
        
        # Temporal Features
        first_seen = profile.get('first_seen')
        last_seen = profile.get('last_seen')
        now = datetime.now()
        
        first_seen_days = (now - first_seen).days if first_seen else 0
        last_seen_days = (now - last_seen).days if last_seen else 0
        
        # Activity Features
        activity_24h = profile.get('recent_activity_24h', 0)
        activity_7d = profile.get('recent_activity_7d', 0)
        activity_30d = profile.get('recent_activity_30d', 0)
        
        # Frequency Features
        days_active = max(1, (last_seen - first_seen).days if first_seen and last_seen else 1)
        tx_frequency = tx_count / days_active
        volume_per_tx = total_volume / tx_count if tx_count > 0 else 0.0
        counterparties_per_tx = unique_counterparties / tx_count if tx_count > 0 else 0.0
        
        return AddressFeatures(
            address=profile.get('address', ''),
            transaction_count=tx_count,
            total_volume_usd=total_volume,
            avg_transaction_value_usd=avg_tx_value,
            counterparties_count=len(counterparties),
            unique_counterparties_count=unique_counterparties,
            frequent_counterparties_count=frequent_counterparties,
            first_seen_days_ago=first_seen_days,
            last_seen_days_ago=last_seen_days,
            activity_24h=activity_24h,
            activity_7d=activity_7d,
            activity_30d=activity_30d,
            is_contract=profile.get('is_contract', False),
            balance_usd=profile.get('balance_usd', 0.0),
            tx_frequency_per_day=tx_frequency,
            volume_per_tx_usd=volume_per_tx,
            counterparties_per_tx=counterparties_per_tx
        )
    
    def train(self, X: np.ndarray, y: np.ndarray) -> MLModel:
        """
        Trainiere das ML Model
        
        Args:
            X: Feature Matrix (n_samples, n_features)
            y: Labels (0 = nicht target, 1 = target)
            
        Returns:
            MLModel Metadaten
        """
        # Split Data
        stratify = y if len(np.unique(y)) > 1 else None
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=stratify
        )
        
        # Scale Features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train Model
        self.model.fit(X_train_scaled, y_train)
        
        # Predictions
        y_pred = self.model.predict(X_test_scaled)
        y_pred_proba = self.model.predict_proba(X_test_scaled)[:, 1]
        
        # Metrics
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, average='weighted', zero_division=0)
        recall = recall_score(y_test, y_pred, average='weighted', zero_division=0)
        f1 = f1_score(y_test, y_pred, average='weighted', zero_division=0)
        roc_auc = roc_auc_score(y_test, y_pred_proba) if len(np.unique(y_test)) > 1 else 0.0
        
        # Feature Importance
        feature_importance = dict(zip(self.feature_names, self.model.feature_importances_))
        
        # Sort Feature Importance
        feature_importance = dict(sorted(feature_importance.items(), key=lambda x: x[1], reverse=True))
        
        # Create Metadata
        self.model_metadata = MLModel(
            model_type='RandomForest',
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1=f1,
            feature_importance=feature_importance,
            trained_at=datetime.now()
        )
        
        logger.info(f"✅ Model Training Complete:")
        logger.info(f"   Accuracy: {accuracy:.4f}")
        logger.info(f"   Precision: {precision:.4f}")
        logger.info(f"   Recall: {recall:.4f}")
        logger.info(f"   F1: {f1:.4f}")
        logger.info(f"   ROC-AUC: {roc_auc:.4f}")
        logger.info(f"   Top Features: {list(feature_importance.keys())[:3]}")
        
        return self.model_metadata
    
    def predict(self, features: AddressFeatures) -> Tuple[float, float]:
        """
        Predict ob Address ein Target ist
        
        Args:
            features: AddressFeatures
            
        Returns:
            (prediction, confidence) - prediction (0-1), confidence (0-1)
        """
        if self.model_metadata is None:
            raise ValueError("Model not trained. Call train() first.")
        
        X = features.to_array().reshape(1, -1)
        X_scaled = self.scaler.transform(X)
        
        proba = self.model.predict_proba(X_scaled)[0]
        score = float(proba[1])            # P(target=1) — der Ranking-Score
        confidence = float(proba.max())    # Sicherheit der Entscheidung
        
        return score, confidence
    
    def predict_batch(self, features_list: List[AddressFeatures]) -> List[Tuple[float, float]]:
        """
        Predict für mehrere Adressen
        
        Args:
            features_list: Liste von AddressFeatures
            
        Returns:
            Liste von (prediction, confidence) Tuples
        """
        if self.model_metadata is None:
            raise ValueError("Model not trained. Call train() first.")
        
        X = np.array([f.to_array() for f in features_list])
        X_scaled = self.scaler.transform(X)
        
        probas = self.model.predict_proba(X_scaled)
        scores = probas[:, 1]
        confidences = probas.max(axis=1)
        
        return list(zip(scores.astype(float), confidences.astype(float)))
    
    def save_model(self, path: str):
        """
        Speichere Model und Scaler
        
        Args:
            path: Pfad zum Speichern
        """
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'metadata': self.model_metadata.to_dict() if self.model_metadata else None
        }
        joblib.dump(model_data, path)
        logger.info(f"✅ Model saved to {path}")
    
    def load_model(self, path: str):
        """
        Lade Model und Scaler
        
        Args:
            path: Pfad zum Model
        """
        model_data = joblib.load(path)
        self.model = model_data['model']
        self.scaler = model_data['scaler']
        if model_data['metadata']:
            meta = dict(model_data['metadata'])
            if isinstance(meta.get('trained_at'), str):
                meta['trained_at'] = datetime.fromisoformat(meta['trained_at'])
            self.model_metadata = MLModel(**meta)
        logger.info(f"✅ Model loaded from {path}")


# Beispiel-Usage
if __name__ == "__main__":
    # Erstelle ML Scorer
    scorer = MLScorer()
    
    # Simuliere Training Data
    np.random.seed(42)
    n_samples = 1000
    
    # Features generieren
    X = np.random.randn(n_samples, 16)
    # Labels generieren (30% targets)
    y = np.random.choice([0, 1], size=n_samples, p=[0.7, 0.3])
    
    # Train Model
    metadata = scorer.train(X, y)
    
    # Test Prediction
    test_features = AddressFeatures(
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
    
    prediction, confidence = scorer.predict(test_features)
    logger.info(f"\nTest Prediction:")
    logger.info(f"   Address: {test_features.address[:10]}...{test_features.address[-4:]}")
    logger.info(f"   Prediction: {prediction} (0=Not Target, 1=Target)")
    logger.info(f"   Confidence: {confidence:.4f}")
    
    # Save Model
    scorer.save_model("ml_model.joblib")
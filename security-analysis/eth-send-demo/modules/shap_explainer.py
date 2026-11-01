"""
SHAP Explainer - SHAP-Explainability für ML-Model
Feature Importance Visualization, SHAP-Values für alle Predictions
Basierend auf State-of-the-Art Explainable AI Research
"""

import numpy as np
from typing import Dict, List
from dataclasses import dataclass
from datetime import datetime
import shap

from modules.logger import Logger

logger = Logger(__name__)


@dataclass
class SHAPExplanation:
    """SHAP Explanation für eine Prediction"""
    address: str
    prediction: float
    confidence: float
    base_value: float
    shap_values: List[float]
    feature_names: List[str]
    feature_values: List[float]
    explanation_text: str
    timestamp: datetime
    
    def to_dict(self) -> dict:
        return {
            'address': self.address,
            'prediction': self.prediction,
            'confidence': self.confidence,
            'base_value': self.base_value,
            'shap_values': self.shap_values,
            'feature_names': self.feature_names,
            'feature_values': self.feature_values,
            'explanation_text': self.explanation_text,
            'timestamp': self.timestamp.isoformat()
        }


class SHAPExplainer:
    """
    SHAP Explainer für ML-Model
    
    Features:
    - SHAP-Integration für RandomForest
    - Feature Importance Visualization
    - SHAP-Values für alle Predictions
    - Explanation API für Frontend
    - Integration mit ML-Scorer
    """
    
    def __init__(self, model, scaler):
        """
        Initialisiere SHAP Explainer
        
        Args:
            model: Trained ML Model
            scaler: StandardScaler
        """
        self.model = model
        self.scaler = scaler
        self.explainer = None
        self.feature_names = [
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
    
    def initialize(self, X_background: np.ndarray):
        """
        Initialisiere SHAP Explainer mit Background Data
        
        Args:
            X_background: Background Data für SHAP (Representative Sample)
        """
        X_scaled = self.scaler.transform(X_background)
        self.explainer = shap.TreeExplainer(self.model)
        self.background_data = X_scaled
        
        logger.info(f"✅ SHAP Explainer initialized with {len(X_background)} background samples")
    
    def explain(self, features: np.ndarray, address: str = "") -> SHAPExplanation:
        """
        Generiere SHAP-Explanation für eine Prediction
        
        Args:
            features: Feature Vector (n_samples, n_features)
            address: Address für die Explanation
            
        Returns:
            SHAPExplanation
        """
        if self.explainer is None:
            raise ValueError("SHAP Explainer not initialized. Call initialize() first.")
        
        # Scale Features
        features_scaled = self.scaler.transform(features)
        
        # Calculate SHAP Values
        shap_values = self.explainer.shap_values(features_scaled)
        
        # Get Prediction
        prediction = self.model.predict(features_scaled)[0]
        prediction_proba = self.model.predict_proba(features_scaled)[0]
        confidence = prediction_proba[1] if len(prediction_proba) > 1 else prediction_proba[0]
        
        # Get Base Value
        base_value = self.explainer.expected_value[1] if len(self.explainer.expected_value) > 1 else self.explainer.expected_value[0]
        
        # Create Explanation Text
        explanation_text = self._generate_explanation_text(
            features, shap_values[0] if len(shap_values.shape) > 2 else shap_values, prediction
        )
        
        return SHAPExplanation(
            address=address,
            prediction=float(prediction),
            confidence=float(confidence),
            base_value=float(base_value),
            shap_values=shap_values[0].tolist() if len(shap_values.shape) > 2 else shap_values.tolist(),
            feature_names=self.feature_names,
            feature_values=features[0].tolist(),
            explanation_text=explanation_text,
            timestamp=datetime.now()
        )
    
    def _generate_explanation_text(self, features: np.ndarray, shap_values: np.ndarray, prediction: float) -> str:
        """
        Generiere human-readable Explanation Text
        
        Args:
            features: Feature Vector
            shap_values: SHAP Values
            prediction: Prediction
            
        Returns:
            Explanation Text
        """
        # Get Top Features
        if len(shap_values.shape) > 2:
            # Multi-class case: use class 1 (positive)
            shap_vals = shap_values[1][0] if len(shap_values) > 1 else shap_values[0]
        else:
            shap_vals = shap_values[0]
        
        feature_importance = dict(zip(self.feature_names, shap_vals))
        top_features = sorted(feature_importance.items(), key=lambda x: abs(x[1]), reverse=True)[:3]
        
        # Generate Text
        if prediction > 0.5:
            explanation = "Die Adresse wurde als TARGET ausgewählt, weil:\n"
        else:
            explanation = "Die Adresse wurde NICHT als Target ausgewählt, weil:\n"
        
        for feature_name, shap_value in top_features:
            feature_value = features[0][self.feature_names.index(feature_name)]
            direction = "erhöht" if shap_value > 0 else "reduziert"
            explanation += f"• {feature_name} ({feature_value:.2f}): {direction} den Score um {abs(shap_value):.3f}\n"
        
        explanation += f"\nBasis-Wert: {self.explainer.expected_value[1] if len(self.explainer.expected_value) > 1 else self.explainer.expected_value[0]:.3f}, Prediction: {prediction:.3f}"
        
        return explanation
    
    def get_feature_importance(self) -> Dict[str, float]:
        """
        Hole Feature Importance vom Model
        
        Returns:
            Dict von Feature Name zu Importance
        """
        if hasattr(self.model, 'feature_importances_'):
            return dict(zip(self.feature_names, self.model.feature_importances_))
        else:
            return {name: 0.0 for name in self.feature_names}
    
    def get_summary_plot_data(self, X: np.ndarray) -> dict:
        """
        Hole Summary Plot Data für Visualization
        
        Args:
            X: Feature Matrix
            
        Returns:
            Summary Plot Data
        """
        if self.explainer is None:
            raise ValueError("SHAP Explainer not initialized. Call initialize() first.")
        
        X_scaled = self.scaler.transform(X)
        shap_values = self.explainer.shap_values(X_scaled)
        
        # Calculate Mean Absolute SHAP Values
        mean_shap = np.abs(shap_values).mean(axis=0)
        
        return {
            'feature_names': self.feature_names,
            'mean_shap_values': mean_shap.tolist(),
            'shap_values': shap_values.tolist(),
            'feature_values': X.tolist()
        }


# Beispiel-Usage
if __name__ == "__main__":
    from modules.ml_scorer import MLScorer
    import numpy as np
    
    # Erstelle ML Scorer
    scorer = MLScorer()
    
    # Generiere Training Data
    np.random.seed(42)
    X = np.random.randn(100, 16)
    y = np.random.choice([0, 1], size=100, p=[0.7, 0.3])
    
    # Train Model
    metadata = scorer.train(X, y)
    
    # Erstelle SHAP Explainer
    explainer = SHAPExplainer(scorer.model, scorer.scaler)
    explainer.initialize(X[:20])  # Background Data
    
    # Test Prediction
    test_features = np.random.randn(1, 16)
    explanation = explainer.explain(test_features, address="0x1234...")
    
    logger.info(f"✅ SHAP Explanation:")
    logger.info(f"   Prediction: {explanation.prediction:.4f}")
    logger.info(f"   Confidence: {explanation.confidence:.4f}")
    logger.info(f"   Base Value: {explanation.base_value:.4f}")
    logger.info(f"   Explanation: {explanation.explanation_text}")
    
    # Feature Importance
    importance = explainer.get_feature_importance()
    logger.info(f"\n✅ Feature Importance:")
    for name, value in sorted(importance.items(), key=lambda x: x[1], reverse=True)[:5]:
        logger.info(f"   {name}: {value:.4f}")
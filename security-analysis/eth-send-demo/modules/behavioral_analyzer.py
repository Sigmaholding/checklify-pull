"""
Behavioral Analyzer - Behavioral Analysis und Pattern Recognition
Temporal Pattern Analysis, Anomaly Detection mit Isolation Forest, Behavioral Clustering
Basierend auf State-of-the-Art Research (CRASE, RiskSEA, AMLHunter)
"""

import numpy as np
from typing import Dict, List
from dataclasses import dataclass
from datetime import datetime, timedelta
from sklearn.ensemble import IsolationForest
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from modules.logger import Logger

logger = Logger(__name__)


@dataclass
class AnomalyDetection:
    """Anomaly Detection Ergebnis"""
    address: str
    is_anomaly: bool
    anomaly_score: float  # -1 bis 1, -1 = anomaly
    anomaly_type: str  # temporal, volume, counterparty, pattern
    description: str
    timestamp: datetime
    confidence: float
    
    def to_dict(self) -> dict:
        return {
            'address': self.address,
            'is_anomaly': self.is_anomaly,
            'anomaly_score': self.anomaly_score,
            'anomaly_type': self.anomaly_type,
            'description': self.description,
            'timestamp': self.timestamp.isoformat(),
            'confidence': self.confidence
        }


@dataclass
class BehavioralCluster:
    """Behavioral Cluster"""
    cluster_id: int
    addresses: List[str]
    cluster_type: str  # high_volume, high_frequency, mixer, normal
    avg_transaction_count: float
    avg_volume_usd: float
    avg_counterparties: float
    timestamp: datetime
    
    def to_dict(self) -> dict:
        return {
            'cluster_id': self.cluster_id,
            'addresses': self.addresses,
            'cluster_type': self.cluster_type,
            'avg_transaction_count': self.avg_transaction_count,
            'avg_volume_usd': self.avg_volume_usd,
            'avg_counterparties': self.avg_counterparties,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class TemporalPattern:
    """Temporales Pattern"""
    address: str
    tx_frequency_per_hour: Dict[int, float]  # Stunde → Frequency
    tx_frequency_per_day: Dict[int, float]  # Wochentag → Frequency
    avg_time_between_tx: float  # Sekunden
    burst_detection: bool  # Burst Activity detected
    regular_pattern: bool  # Regular Pattern detected
    timestamp: datetime
    
    def to_dict(self) -> dict:
        return {
            'address': self.address,
            'tx_frequency_per_hour': self.tx_frequency_per_hour,
            'tx_frequency_per_day': self.tx_frequency_per_day,
            'avg_time_between_tx': self.avg_time_between_tx,
            'burst_detection': self.burst_detection,
            'regular_pattern': self.regular_pattern,
            'timestamp': self.timestamp.isoformat()
        }


class BehavioralAnalyzer:
    """
    Behavioral Analyzer für Address Analysis
    
    Features:
    - Temporal Pattern Analysis (Transaction Frequency, Time-of-Day)
    - Anomaly Detection mit Isolation Forest
    - Behavioral Clustering mit K-Means
    - Pattern Recognition für Wash-Trading
    - Integration mit ML-Scorer
    """
    
    def __init__(self):
        """Initialisiere Behavioral Analyzer"""
        self.anomaly_detector = IsolationForest(
            contamination=0.1,
            random_state=42,
            n_jobs=-1
        )
        self.clusterer = KMeans(
            n_clusters=4,
            random_state=42,
            n_init=10
        )
        self.scaler = StandardScaler()
    
    def analyze_temporal_pattern(self, transactions: List[dict]) -> TemporalPattern:
        """
        Analysiere temporales Pattern
        
        Args:
            transactions: Liste von Transaktionen
            
        Returns:
            TemporalPattern
        """
        if not transactions:
            return TemporalPattern(
                address="",
                tx_frequency_per_hour={},
                tx_frequency_per_day={},
                avg_time_between_tx=0.0,
                burst_detection=False,
                regular_pattern=False,
                timestamp=datetime.now()
            )
        
        address = transactions[0].get('address', '')
        
        # Extrahiere Timestamps
        timestamps = [datetime.fromisoformat(tx['timestamp']) for tx in transactions if 'timestamp' in tx]
        
        if not timestamps:
            return TemporalPattern(
                address=address,
                tx_frequency_per_hour={},
                tx_frequency_per_day={},
                avg_time_between_tx=0.0,
                burst_detection=False,
                regular_pattern=False,
                timestamp=datetime.now()
            )
        
        # Frequency per Hour
        freq_per_hour = {}
        for ts in timestamps:
            hour = ts.hour
            freq_per_hour[hour] = freq_per_hour.get(hour, 0) + 1
        
        # Frequency per Day
        freq_per_day = {}
        for ts in timestamps:
            day = ts.weekday()  # 0 = Monday, 6 = Sunday
            freq_per_day[day] = freq_per_day.get(day, 0) + 1
        
        # Average Time Between Transactions
        if len(timestamps) > 1:
            timestamps_sorted = sorted(timestamps)
            time_diffs = [(timestamps_sorted[i+1] - timestamps_sorted[i]).total_seconds() 
                          for i in range(len(timestamps_sorted)-1)]
            avg_time_between = np.mean(time_diffs) if time_diffs else 0.0
        else:
            avg_time_between = 0.0
        
        # Burst Detection (mehr als 10 Transaktionen in 1 Stunde)
        burst_detected = any(count > 10 for count in freq_per_hour.values())
        
        # Regular Pattern Detection (consistent frequency across days)
        if freq_per_day:
            freq_values = list(freq_per_day.values())
            regular_pattern = np.std(freq_values) < np.mean(freq_values) * 0.5
        else:
            regular_pattern = False
        
        return TemporalPattern(
            address=address,
            tx_frequency_per_hour=freq_per_hour,
            tx_frequency_per_day=freq_per_day,
            avg_time_between_tx=avg_time_between,
            burst_detection=burst_detected,
            regular_pattern=regular_pattern,
            timestamp=datetime.now()
        )
    
    def detect_anomalies(self, profiles: List[dict]) -> List[AnomalyDetection]:
        """
        Detect Anomalies mit Isolation Forest
        
        Args:
            profiles: Liste von Address Profiles
            
        Returns:
            Liste von AnomalyDetection
        """
        if len(profiles) < 10:
            return []
        
        # Extrahiere Features
        features = []
        addresses = []
        
        for profile in profiles:
            feature_vector = [
                profile.get('transaction_count', 0),
                profile.get('total_volume_usd', 0.0),
                profile.get('avg_transaction_value_usd', 0.0),
                len(profile.get('counterparties', [])),
                profile.get('balance_usd', 0.0),
                profile.get('recent_activity_24h', 0),
                profile.get('recent_activity_7d', 0),
                profile.get('recent_activity_30d', 0)
            ]
            features.append(feature_vector)
            addresses.append(profile.get('address', ''))
        
        # Scale Features
        features_scaled = self.scaler.fit_transform(features)
        
        # Detect Anomalies
        anomaly_scores = self.anomaly_detector.fit_predict(features_scaled)
        
        # Create AnomalyDetection Objects
        anomalies = []
        for addr, score in zip(addresses, anomaly_scores):
            if score == -1:  # Anomaly
                profile = next(p for p in profiles if p.get('address') == addr)
                
                # Bestimme Anomaly Type
                tx_count = profile.get('transaction_count', 0)
                volume = profile.get('total_volume_usd', 0.0)
                activity_24h = profile.get('recent_activity_24h', 0)
                
                if activity_24h > 100:
                    anomaly_type = "temporal"
                    description = "Extrem hohe Aktivität in den letzten 24h"
                elif volume > 1000000:
                    anomaly_type = "volume"
                    description = "Ungewöhnlich hohes Volumen"
                elif tx_count > 1000:
                    anomaly_type = "pattern"
                    description = "Ungewöhnlich viele Transaktionen"
                else:
                    anomaly_type = "counterparty"
                    description = "Ungewöhnliche Counterparty-Struktur"
                
                anomalies.append(AnomalyDetection(
                    address=addr,
                    is_anomaly=True,
                    anomaly_score=float(score),
                    anomaly_type=anomaly_type,
                    description=description,
                    timestamp=datetime.now(),
                    confidence=0.8
                ))
        
        return anomalies
    
    def cluster_behavior(self, profiles: List[dict]) -> List[BehavioralCluster]:
        """
        Cluster Adressen nach Verhalten
        
        Args:
            profiles: Liste von Address Profiles
            
        Returns:
            Liste von BehavioralCluster
        """
        if len(profiles) < 4:
            return []
        
        # Extrahiere Features
        features = []
        addresses = []
        
        for profile in profiles:
            feature_vector = [
                profile.get('transaction_count', 0),
                profile.get('total_volume_usd', 0.0),
                profile.get('avg_transaction_value_usd', 0.0),
                len(profile.get('counterparties', [])),
                profile.get('balance_usd', 0.0),
                profile.get('recent_activity_24h', 0),
                profile.get('recent_activity_7d', 0),
                profile.get('recent_activity_30d', 0)
            ]
            features.append(feature_vector)
            addresses.append(profile.get('address', ''))
        
        # Scale Features
        features_scaled = self.scaler.fit_transform(features)
        
        # Cluster
        cluster_labels = self.clusterer.fit_predict(features_scaled)
        
        # Create Cluster Objects
        clusters = {}
        for addr, label in zip(addresses, cluster_labels):
            if label not in clusters:
                clusters[label] = {
                    'addresses': [],
                    'tx_counts': [],
                    'volumes': [],
                    'counterparties': []
                }
            profile = next(p for p in profiles if p.get('address') == addr)
            clusters[label]['addresses'].append(addr)
            clusters[label]['tx_counts'].append(profile.get('transaction_count', 0))
            clusters[label]['volumes'].append(profile.get('total_volume_usd', 0.0))
            clusters[label]['counterparties'].append(len(profile.get('counterparties', [])))
        
        # Determine Cluster Types
        cluster_objects = []
        for cluster_id, data in clusters.items():
            avg_tx = np.mean(data['tx_counts'])
            avg_volume = np.mean(data['volumes'])
            avg_counterparties = np.mean(data['counterparties'])
            
            # Cluster Type Bestimmung
            if avg_volume > 1000000:
                cluster_type = "high_volume"
            elif avg_tx > 100:
                cluster_type = "high_frequency"
            elif avg_counterparties > 50:
                cluster_type = "mixer"
            else:
                cluster_type = "normal"
            
            cluster_objects.append(BehavioralCluster(
                cluster_id=int(cluster_id),
                addresses=data['addresses'],
                cluster_type=cluster_type,
                avg_transaction_count=float(avg_tx),
                avg_volume_usd=float(avg_volume),
                avg_counterparties=float(avg_counterparties),
                timestamp=datetime.now()
            ))
        
        return cluster_objects
    
    def detect_wash_trading(self, transactions: List[dict]) -> Dict[str, float]:
        """
        Detect Wash-Trading Pattern
        
        Args:
            transactions: Liste von Transaktionen
            
        Returns:
            Dict mit Wash-Trading Score
        """
        if len(transactions) < 10:
            return {'wash_trading_score': 0.0, 'confidence': 0.0}
        
        # Group by Counterparty
        counterparty_txs = {}
        for tx in transactions:
            cp = tx.get('to_address', tx.get('counterpart', ''))
            if cp not in counterparty_txs:
                counterparty_txs[cp] = []
            counterparty_txs[cp].append(tx)
        
        # Detect Circular Transactions
        circular_score = 0.0
        for cp, txs in counterparty_txs.items():
            if len(txs) > 5:
                # Prüfe ob来回 Transaktionen
                from_addrs = [tx.get('from_address', '') for tx in txs]
                if len(set(from_addrs)) < len(txs) * 0.5:
                    circular_score += 1.0
        
        # Detect Same-Amount Transactions
        amounts = [tx.get('amount', 0) for tx in transactions]
        amount_variance = np.var(amounts) if amounts else 0.0
        same_amount_score = 1.0 / (1.0 + amount_variance) if amount_variance > 0 else 0.0
        
        # Combined Score
        wash_score = (circular_score + same_amount_score) / 2.0
        confidence = min(1.0, len(transactions) / 100.0)
        
        return {
            'wash_trading_score': wash_score,
            'circular_score': circular_score,
            'same_amount_score': same_amount_score,
            'confidence': confidence
        }


# Beispiel-Usage
if __name__ == "__main__":
    analyzer = BehavioralAnalyzer()
    
    # Simuliere Profiles
    profiles = [
        {
            'address': f"0x{i:040x}",
            'transaction_count': 100 + i * 10,
            'total_volume_usd': 1000000.0 + i * 100000,
            'avg_transaction_value_usd': 10000.0,
            'counterparties': [f"0x{j:040x}" for j in range(10 + i)],
            'balance_usd': 50000.0,
            'recent_activity_24h': 5 + i,
            'recent_activity_7d': 20 + i * 2,
            'recent_activity_30d': 50 + i * 5
        }
        for i in range(20)
    ]
    
    # Anomalies detecten
    anomalies = analyzer.detect_anomalies(profiles)
    logger.info(f"✅ Anomalies detected: {len(anomalies)}")
    for anomaly in anomalies[:3]:
        logger.info(f"   {anomaly.address[:10]}...{anomaly.address[-4:]}: {anomaly.anomaly_type} - {anomaly.description}")
    
    # Clustering
    clusters = analyzer.cluster_behavior(profiles)
    logger.info(f"\n✅ Clusters found: {len(clusters)}")
    for cluster in clusters:
        logger.info(f"   Cluster {cluster.cluster_id}: {cluster.cluster_type} ({len(cluster.addresses)} addresses)")
    
    # Temporal Pattern
    transactions = [
        {
            'address': '0x1234567890123456789012345678901234567890',
            'timestamp': (datetime.now() - timedelta(hours=i)).isoformat()
        }
        for i in range(50)
    ]
    pattern = analyzer.analyze_temporal_pattern(transactions)
    logger.info(f"\n✅ Temporal Pattern:")
    logger.info(f"   Burst Detection: {pattern.burst_detection}")
    logger.info(f"   Regular Pattern: {pattern.regular_pattern}")
    logger.info(f"   Avg Time Between TX: {pattern.avg_time_between_tx:.2f}s")
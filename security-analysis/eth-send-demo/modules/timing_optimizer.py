"""
Timing Optimizer - Timing-Optimierung für < 60s Poisoning
Adaptive Timing, Gas Price Optimization, Confirmation Time Tracking
Basierend auf State-of-the-Art MEV und Timing Optimization Research
"""

import asyncio
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np

from modules.logger import Logger

logger = Logger(__name__)


@dataclass
class TimingOptimization:
    """Timing Optimization Result"""
    optimal_delay_seconds: int
    max_delay_seconds: int
    min_delay_seconds: int
    gas_price_gwei: float
    expected_confirmation_seconds: int
    network_congestion: float
    confidence: float
    
    def to_dict(self) -> dict:
        return {
            'optimal_delay_seconds': self.optimal_delay_seconds,
            'max_delay_seconds': self.max_delay_seconds,
            'min_delay_seconds': self.min_delay_seconds,
            'gas_price_gwei': self.gas_price_gwei,
            'expected_confirmation_seconds': self.expected_confirmation_seconds,
            'network_congestion': self.network_congestion,
            'confidence': self.confidence
        }


@dataclass
class NetworkConditions:
    """Network Conditions für Timing Optimization"""
    block_time_seconds: int
    gas_price_gwei: float
    network_congestion: float
    mempool_size: int
    confirmation_depth: int
    
    def to_dict(self) -> dict:
        return {
            'block_time_seconds': self.block_time_seconds,
            'gas_price_gwei': self.gas_price_gwei,
            'network_congestion': self.network_congestion,
            'mempool_size': self.mempool_size,
            'confirmation_depth': self.confirmation_depth
        }


class TimingOptimizer:
    """
    Timing Optimizer für < 60s Poisoning
    
    Features:
    - Adaptive Timing basierend auf Network Conditions
    - Gas Price Optimization
    - Confirmation Time Tracking
    - Speed Optimization für < 60s Poisoning
    - Historical Timing Analysis
    """
    
    def __init__(self):
        """Initialisiere Timing Optimizer"""
        self.timing_history: List[Dict] = []
        self.network_conditions: Optional[NetworkConditions] = None
        self.optimization_cache: Dict[str, TimingOptimization] = {}
    
    async def optimize_timing(self, network_conditions: NetworkConditions, target_confirmation_seconds: int = 60) -> TimingOptimization:
        """
        Optimiere Timing für Target Confirmation Time
        
        Args:
            network_conditions: Aktuelle Network Conditions
            target_confirmation_seconds: Target Confirmation Time (default: 60s)
            
        Returns:
            TimingOptimization
        """
        self.network_conditions = network_conditions
        
        # Berechne optimalen Delay
        optimal_delay = self._calculate_optimal_delay(network_conditions, target_confirmation_seconds)
        
        # Berechne Gas Price
        gas_price = self._calculate_optimal_gas_price(network_conditions)
        
        # Berechne expected Confirmation Time
        expected_confirmation = self._calculate_expected_confirmation(network_conditions, gas_price)
        
        # Berechne Confidence
        confidence = self._calculate_confidence(network_conditions, expected_confirmation, target_confirmation_seconds)
        
        optimization = TimingOptimization(
            optimal_delay_seconds=optimal_delay,
            max_delay_seconds=optimal_delay * 2,
            min_delay_seconds=max(0, optimal_delay // 2),
            gas_price_gwei=gas_price,
            expected_confirmation_seconds=expected_confirmation,
            network_congestion=network_conditions.network_congestion,
            confidence=confidence
        )
        
        # Cache Result
        cache_key = f"{network_conditions.block_time_seconds}_{network_conditions.gas_price_gwei}_{network_conditions.network_congestion}"
        self.optimization_cache[cache_key] = optimization
        
        # Log Result
        self.timing_history.append({
            'timestamp': datetime.now().isoformat(),
            'optimization': optimization.to_dict(),
            'network_conditions': network_conditions.to_dict()
        })
        
        # Begrenze History
        if len(self.timing_history) > 1000:
            self.timing_history = self.timing_history[-1000:]
        
        return optimization
    
    def _calculate_optimal_delay(self, network_conditions: NetworkConditions, target_confirmation_seconds: int) -> int:
        """
        Berechne optimalen Delay
        
        Args:
            network_conditions: Network Conditions
            target_confirmation_seconds: Target Confirmation Time
            
        Returns:
            Optimal Delay in Sekunden
        """
        # Basis Delay: Block Time * Confirmation Depth
        base_delay = network_conditions.block_time_seconds * network_conditions.confirmation_depth
        
        # Adjust für Network Congestion
        congestion_factor = 1.0 + (network_conditions.network_congestion * 0.5)
        adjusted_delay = base_delay * congestion_factor
        
        # Adjust für Mempool Size
        mempool_factor = 1.0 + (network_conditions.mempool_size / 100000)
        adjusted_delay = adjusted_delay * mempool_factor
        
        # Ensure < target_confirmation_seconds
        optimal_delay = min(adjusted_delay, target_confirmation_seconds)
        
        return int(optimal_delay)
    
    def _calculate_optimal_gas_price(self, network_conditions: NetworkConditions) -> float:
        """
        Berechne optimalen Gas Price
        
        Args:
            network_conditions: Network Conditions
            
        Returns:
            Gas Price in Gwei
        """
        # Basis Gas Price
        base_gas_price = network_conditions.gas_price_gwei
        
        # Adjust für Network Congestion
        congestion_premium = network_conditions.network_congestion * 10.0
        adjusted_gas_price = base_gas_price + congestion_premium
        
        # Adjust für Speed Requirements
        speed_premium = 5.0 if network_conditions.network_congestion > 0.7 else 0.0
        adjusted_gas_price += speed_premium
        
        return round(adjusted_gas_price, 2)
    
    def _calculate_expected_confirmation(self, network_conditions: NetworkConditions, gas_price: float) -> int:
        """
        Berechne expected Confirmation Time
        
        Args:
            network_conditions: Network Conditions
            gas_price: Gas Price
            
        Returns:
            Expected Confirmation Time in Sekunden
        """
        # Basis Confirmation Time
        base_time = network_conditions.block_time_seconds * network_conditions.confirmation_depth
        
        # Adjust für Gas Price (höher = schneller)
        gas_price_factor = gas_price / network_conditions.gas_price_gwei
        adjusted_time = base_time / gas_price_factor
        
        # Adjust für Network Congestion
        congestion_factor = 1.0 + (network_conditions.network_congestion * 0.3)
        adjusted_time = adjusted_time * congestion_factor
        
        return int(adjusted_time)
    
    def _calculate_confidence(self, network_conditions: NetworkConditions, expected_confirmation: int, target_confirmation: int) -> float:
        """
        Berechne Confidence für Timing Optimization
        
        Args:
            network_conditions: Network Conditions
            expected_confirmation: Expected Confirmation Time
            target_confirmation: Target Confirmation Time
            
        Returns:
            Confidence Score (0-1)
        """
        # Basis Confidence
        confidence = 0.5
        
        # Adjust für Expected vs Target
        if expected_confirmation <= target_confirmation:
            confidence += 0.3
        elif expected_confirmation <= target_confirmation * 1.5:
            confidence += 0.1
        else:
            confidence -= 0.2
        
        # Adjust für Network Stability
        if network_conditions.network_congestion < 0.5:
            confidence += 0.2
        elif network_conditions.network_congestion > 0.8:
            confidence -= 0.1
        
        # Adjust für Historical Performance
        if self.timing_history:
            recent_success_rate = self._calculate_recent_success_rate()
            confidence += recent_success_rate * 0.2
        
        return max(0.0, min(1.0, confidence))
    
    def _calculate_recent_success_rate(self) -> float:
        """
        Berechne Recent Success Rate
        
        Returns:
            Success Rate (0-1)
        """
        if not self.timing_history:
            return 0.5
        
        # Letzte 10 Optimierungen
        recent = self.timing_history[-10:]
        
        # Success = Expected Confirmation <= Target Confirmation
        successes = sum(1 for entry in recent if entry['optimization']['expected_confirmation_seconds'] <= 60)
        
        return successes / len(recent)
    
    def get_timing_history(self, limit: int = 100) -> List[Dict]:
        """Hole Timing History"""
        return self.timing_history[-limit:]
    
    def get_cached_optimization(self, network_conditions: NetworkConditions) -> Optional[TimingOptimization]:
        """
        Hole cached Optimization
        
        Args:
            network_conditions: Network Conditions
            
        Returns:
            Cached TimingOptimization oder None
        """
        cache_key = f"{network_conditions.block_time_seconds}_{network_conditions.gas_price_gwei}_{network_conditions.network_congestion}"
        return self.optimization_cache.get(cache_key)


# Beispiel-Usage
async def main():
    optimizer = TimingOptimizer()
    
    # Simuliere Network Conditions
    conditions = NetworkConditions(
        block_time_seconds=12,
        gas_price_gwei=25.0,
        network_congestion=0.6,
        mempool_size=150000,
        confirmation_depth=3
    )
    
    # Optimiere Timing
    optimization = await optimizer.optimize_timing(conditions, target_confirmation_seconds=60)
    
    logger.info(f"✅ Timing Optimization:")
    logger.info(f"   Optimal Delay: {optimization.optimal_delay_seconds}s")
    logger.info(f"   Gas Price: {optimization.gas_price_gwei} Gwei")
    logger.info(f"   Expected Confirmation: {optimization.expected_confirmation_seconds}s")
    logger.info(f"   Confidence: {optimization.confidence:.2f}")
    logger.info(f"   Network Congestion: {optimization.network_congestion:.2f}")


if __name__ == "__main__":
    asyncio.run(main())
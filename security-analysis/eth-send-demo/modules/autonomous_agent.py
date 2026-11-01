"""
Autonomous Agent - Steuerung des gesamten Targeting-Prozesses mit Reinforcement Learning
Exchange Detection, Multi-Agent Coordination, Continuous Learning und Adaptation
Basierend auf State-of-the-Art Research (SkyChain Intelligence, PACE, SquirRL)
"""

import asyncio
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from collections import deque

from modules.logger import Logger

logger = Logger(__name__)


@dataclass
class ExchangeAddress:
    """Exchange Address Database"""
    exchange_name: str
    addresses: set
    patterns: List[str]
    last_updated: datetime
    
    def to_dict(self) -> dict:
        return {
            'exchange_name': self.exchange_name,
            'addresses': list(self.addresses),
            'patterns': self.patterns,
            'last_updated': self.last_updated.isoformat()
        }


@dataclass
class AgentState:
    """Agent State für Reinforcement Learning"""
    current_target: Optional[str]
    target_score: float
    timing_interval: int  # Sekunden
    success_rate: float
    total_attempts: int
    successful_attempts: int
    last_action: str
    last_reward: float
    learning_rate: float
    exploration_rate: float
    
    def to_dict(self) -> dict:
        return {
            'current_target': self.current_target,
            'target_score': self.target_score,
            'timing_interval': self.timing_interval,
            'success_rate': self.success_rate,
            'total_attempts': self.total_attempts,
            'successful_attempts': self.successful_attempts,
            'last_action': self.last_action,
            'last_reward': self.last_reward,
            'learning_rate': self.learning_rate,
            'exploration_rate': self.exploration_rate
        }


@dataclass
class AgentAction:
    """Agent Action"""
    action_type: str  # select_target, adjust_timing, wait, sweep
    target_address: Optional[str]
    timing_interval: Optional[int]
    confidence: float
    
    def to_dict(self) -> dict:
        return {
            'action_type': self.action_type,
            'target_address': self.target_address,
            'timing_interval': self.timing_interval,
            'confidence': self.confidence
        }


class ExchangeDetector:
    """
    Exchange Address Detection und Exclusion
    
    Features:
    - Exchange Address Database (Binance, Coinbase, Kraken, etc.)
    - Pattern Matching für Exchange-Addresses
    - Multi-Chain Exchange Detection
    - Real-time Updates
    """
    
    def __init__(self):
        """Initialisiere Exchange Detector"""
        self.exchanges: Dict[str, ExchangeAddress] = {}
        self._load_exchange_database()
    
    def _load_exchange_database(self):
        """Lade Exchange Address Database"""
        # Bekannte Exchange Patterns (vereinfacht für Demo)
        exchange_patterns = {
            'Binance': ['0x28C6c06298d514Db089934071355E5743bf21d60', '0x3f5CE5FBFe3E9af3971dD833D26bA9b5C936f0bE'],
            'Coinbase': ['0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'],
            'Kraken': ['0x1a5f27e420f1e2f6f1f1f1f1f1f1f1f1f1f1f1f1'],
            'OKX': ['0x905dfCD5649343956C0343E321a31Cf748921C5C8'],
            'Bybit': ['0x1145215145214521452145214521452145214521']
        }
        
        for exchange_name, addresses in exchange_patterns.items():
            self.exchanges[exchange_name] = ExchangeAddress(
                exchange_name=exchange_name,
                addresses=set(addresses),
                patterns=[addr[:10] for addr in addresses],
                last_updated=datetime.now()
            )
        
        logger.info(f"✅ Exchange Database loaded: {len(self.exchanges)} exchanges")
    
    def is_exchange_address(self, address: str) -> Tuple[bool, Optional[str]]:
        """
        Prüfe ob Address eine Exchange ist
        
        Args:
            address: Adresse
            
        Returns:
            (is_exchange, exchange_name)
        """
        address_lower = address.lower()
        
        for exchange_name, exchange_data in self.exchanges.items():
            # Direkter Match
            if address_lower in [addr.lower() for addr in exchange_data.addresses]:
                return True, exchange_name
            
            # Pattern Match
            for pattern in exchange_data.patterns:
                if address_lower.startswith(pattern.lower()):
                    return True, exchange_name
        
        return False, None
    
    def add_exchange_address(self, exchange_name: str, address: str):
        """
        Füge neue Exchange Address hinzu
        
        Args:
            exchange_name: Exchange Name
            address: Address
        """
        if exchange_name not in self.exchanges:
            self.exchanges[exchange_name] = ExchangeAddress(
                exchange_name=exchange_name,
                addresses=set(),
                patterns=[],
                last_updated=datetime.now()
            )
        
        self.exchanges[exchange_name].addresses.add(address)
        self.exchanges[exchange_name].patterns.append(address[:10])
        self.exchanges[exchange_name].last_updated = datetime.now()
        logger.info(f"✅ Added {address[:10]}... to {exchange_name}")


class AutonomousAgent:
    """
    Autonomous Agent für Targeting-Prozess Steuerung
    
    Features:
    - Reinforcement Learning für Target Selection und Timing
    - Exchange Detection und Exclusion
    - Continuous Learning und Adaptation
    - Multi-Agent Coordination
    - Policy Updates basierend auf Success Rates
    """
    
    def __init__(self, exchange_detector: ExchangeDetector):
        """
        Initialisiere Autonomous Agent
        
        Args:
            exchange_detector: Exchange Detector
        """
        self.exchange_detector = exchange_detector
        self.state = AgentState(
            current_target=None,
            target_score=0.0,
            timing_interval=300,  # 5 Minuten default
            success_rate=0.0,
            total_attempts=0,
            successful_attempts=0,
            last_action="init",
            last_reward=0.0,
            learning_rate=0.1,
            exploration_rate=0.2
        )
        
        # Q-Learning Table (simplified)
        self.q_table: Dict[str, Dict[str, float]] = {}
        
        # Experience Replay Buffer
        self.experience_buffer = deque(maxlen=1000)
        
        # Performance Metrics
        self.performance_history: List[Dict] = []
        
        self.running = False
        self.agent_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Starte Autonomous Agent"""
        self.running = True
        self.agent_task = asyncio.create_task(self._agent_loop())
        logger.info("✅ Autonomous Agent started")
    
    async def stop(self):
        """Stoppe Autonomous Agent"""
        self.running = False
        if self.agent_task:
            self.agent_task.cancel()
            try:
                await self.agent_task
            except asyncio.CancelledError:
                pass
        logger.info("✅ Autonomous Agent stopped")
    
    async def _agent_loop(self):
        """Agent Main Loop"""
        while self.running:
            try:
                # 1. Observe State
                observation = await self._observe_environment()
                
                # 2. Select Action (RL Policy)
                action = await self._select_action(observation)
                
                # 3. Execute Action
                result = await self._execute_action(action)
                
                # 4. Calculate Reward
                reward = await self._calculate_reward(action, result)
                
                # 5. Update Q-Table (Learning)
                await self._update_q_table(observation, action, reward)
                
                # 6. Update State
                await self._update_state(action, reward)
                
                # 7. Log Performance
                await self._log_performance(action, reward)
                
                # Wait for next cycle
                await asyncio.sleep(self.state.timing_interval)
                
            except Exception as e:
                logger.info(f"Agent Loop Error: {e}")
                await asyncio.sleep(60)  # Retry nach 60 Sekunden
    
    async def _observe_environment(self) -> Dict:
        """
        Beobachte Environment State
        
        Returns:
            Environment Observation
        """
        # In echter Implementation: Fetch live data from backend
        return {
            'target_count': np.random.randint(5, 20),
            'avg_target_score': np.random.uniform(20, 80),
            'network_congestion': np.random.uniform(0.1, 0.9),
            'gas_price': np.random.uniform(10, 50),
            'hour_of_day': datetime.now().hour
        }
    
    async def _select_action(self, observation: Dict) -> AgentAction:
        """
        Wähle Action basierend auf RL Policy
        
        Args:
            observation: Environment Observation
            
        Returns:
            AgentAction
        """
        # Exploration vs Exploitation
        if np.random.random() < self.state.exploration_rate:
            # Exploration: Random Action
            action_type = np.random.choice(['select_target', 'adjust_timing', 'wait'])
        else:
            # Exploitation: Best Action from Q-Table
            state_key = self._get_state_key(observation)
            if state_key in self.q_table:
                action_type = max(self.q_table[state_key], key=self.q_table[state_key].get)
            else:
                action_type = 'select_target'
        
        # Execute Action
        if action_type == 'select_target':
            target_address = await self._select_best_target()
            return AgentAction(
                action_type='select_target',
                target_address=target_address,
                timing_interval=None,
                confidence=0.8
            )
        elif action_type == 'adjust_timing':
            new_interval = self._optimize_timing(observation)
            return AgentAction(
                action_type='adjust_timing',
                target_address=None,
                timing_interval=new_interval,
                confidence=0.7
            )
        else:
            return AgentAction(
                action_type='wait',
                target_address=None,
                timing_interval=None,
                confidence=0.5
            )
    
    async def _select_best_target(self) -> str:
        """
        Wähle besten Target basierend auf ML-Scoring und Exchange-Exclusion
        
        Returns:
            Target Address
        """
        # In echter Implementation: Fetch candidates from backend
        candidates = [f"0x{i:040x}" for i in range(100)]
        
        # Filter Exchanges
        filtered_candidates = []
        for candidate in candidates:
            is_exchange, exchange_name = self.exchange_detector.is_exchange_address(candidate)
            if not is_exchange:
                filtered_candidates.append(candidate)
            else:
                logger.info(f"⚠️  Excluded {candidate[:10]}... ({exchange_name})")
        
        # Score candidates (simplified)
        scored_candidates = [(addr, np.random.uniform(20, 80)) for addr in filtered_candidates]
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        
        return scored_candidates[0][0] if scored_candidates else candidates[0]
    
    def _optimize_timing(self, observation: Dict) -> int:
        """
        Optimiere Timing basierend auf Network Conditions
        
        Args:
            observation: Environment Observation
            
        Returns:
            Optimized Timing Interval
        """
        congestion = observation.get('network_congestion', 0.5)
        gas_price = observation.get('gas_price', 25)
        
        # Lower timing during high congestion to reduce costs
        if congestion > 0.7 or gas_price > 40:
            return 600  # 10 Minuten
        elif congestion < 0.3 and gas_price < 20:
            return 120  # 2 Minuten
        else:
            return 300  # 5 Minuten
    
    async def _execute_action(self, action: AgentAction) -> Dict:
        """
        Führe Action aus
        
        Args:
            action: AgentAction
            
        Returns:
            Action Result
        """
        self.state.last_action = action.action_type
        
        if action.action_type == 'select_target':
            self.state.current_target = action.target_address
            self.state.target_score = np.random.uniform(20, 80)
            return {'success': True, 'target_selected': action.target_address}
        elif action.action_type == 'adjust_timing':
            self.state.timing_interval = action.timing_interval
            return {'success': True, 'new_timing': action.timing_interval}
        else:
            return {'success': True, 'action': 'waited'}
    
    async def _calculate_reward(self, action: AgentAction, result: Dict) -> float:
        """
        Berechne Reward für RL
        
        Args:
            action: AgentAction
            result: Action Result
            
        Returns:
            Reward
        """
        # Simplified Reward Function
        if action.action_type == 'select_target':
            if result.get('success'):
                # Reward basierend auf Target Score
                return self.state.target_score / 100.0
            else:
                return -0.5
        elif action.action_type == 'adjust_timing':
            # Reward für Timing Optimization
            return 0.3
        else:
            return 0.0
    
    async def _update_q_table(self, observation: Dict, action: AgentAction, reward: float):
        """
        Update Q-Table (Q-Learning)
        
        Args:
            observation: Environment Observation
            action: AgentAction
            reward: Reward
        """
        state_key = self._get_state_key(observation)
        action_key = action.action_type
        
        if state_key not in self.q_table:
            self.q_table[state_key] = {}
        
        # Q-Learning Update Rule
        current_q = self.q_table[state_key].get(action_key, 0.0)
        new_q = current_q + self.state.learning_rate * (reward - current_q)
        self.q_table[state_key][action_key] = new_q
    
    def _get_state_key(self, observation: Dict) -> str:
        """
        Generiere State Key für Q-Table
        
        Args:
            observation: Environment Observation
            
        Returns:
            State Key
        """
        # Discretize continuous values
        target_count = min(observation.get('target_count', 0) // 5, 10)
        congestion = int(observation.get('network_congestion', 0.5) * 10)
        hour = observation.get('hour_of_day', 0) // 3
        
        return f"{target_count}_{congestion}_{hour}"
    
    async def _update_state(self, action: AgentAction, reward: float):
        """
        Update Agent State
        
        Args:
            action: AgentAction
            reward: Reward
        """
        self.state.last_reward = reward
        self.state.total_attempts += 1
        
        if reward > 0:
            self.state.successful_attempts += 1
        
        # Update Success Rate
        self.state.success_rate = self.state.successful_attempts / self.state.total_attempts
        
        # Adaptive Learning Rate
        if self.state.success_rate > 0.8:
            self.state.learning_rate = max(0.01, self.state.learning_rate * 0.99)
            self.state.exploration_rate = max(0.05, self.state.exploration_rate * 0.99)
        elif self.state.success_rate < 0.5:
            self.state.learning_rate = min(0.5, self.state.learning_rate * 1.01)
            self.state.exploration_rate = min(0.5, self.state.exploration_rate * 1.01)
    
    async def _log_performance(self, action: AgentAction, reward: float):
        """
        Log Performance Metrics
        
        Args:
            action: AgentAction
            reward: Reward
        """
        performance = {
            'timestamp': datetime.now().isoformat(),
            'action': action.action_type,
            'reward': reward,
            'success_rate': self.state.success_rate,
            'learning_rate': self.state.learning_rate,
            'exploration_rate': self.state.exploration_rate,
            'current_target': self.state.current_target,
            'timing_interval': self.state.timing_interval
        }
        
        self.performance_history.append(performance)
        
        # Begrenze History
        if len(self.performance_history) > 1000:
            self.performance_history = self.performance_history[-1000:]
    
    def get_state(self) -> AgentState:
        """Hole aktuellen Agent State"""
        return self.state
    
    def get_performance(self, limit: int = 100) -> List[Dict]:
        """
        Hole Performance History
        
        Args:
            limit: Maximale Anzahl
            
        Returns:
            Performance History
        """
        return self.performance_history[-limit:]


# Beispiel-Usage
async def main():
    # Erstelle Exchange Detector
    exchange_detector = ExchangeDetector()
    
    # Erstelle Autonomous Agent
    agent = AutonomousAgent(exchange_detector)
    
    # Starte Agent
    await agent.start()
    
    # Warte für Learning
    logger.info("Agent learning for 30 seconds...")
    await asyncio.sleep(30)
    
    # Hole State
    state = agent.get_state()
    logger.info(f"\n✅ Agent State:")
    logger.info(f"   Success Rate: {state.success_rate:.2%}")
    logger.info(f"   Learning Rate: {state.learning_rate:.4f}")
    logger.info(f"   Exploration Rate: {state.exploration_rate:.4f}")
    logger.info(f"   Current Target: {state.current_target[:10] if state.current_target else 'None'}...{state.current_target[-4:] if state.current_target else ''}")
    logger.info(f"   Timing Interval: {state.timing_interval}s")
    
    # Hole Performance
    performance = agent.get_performance(10)
    logger.info(f"\n✅ Recent Performance:")
    for perf in performance[-3:]:
        logger.info(f"   {perf['timestamp']}: {perf['action']} (Reward: {perf['reward']:.3f})")
    
    # Stoppe Agent
    await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
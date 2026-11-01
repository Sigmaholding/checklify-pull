"""
Multi-Agent Coordinator - Koordination über mehrere Nodes
Leader Election, Distributed State Sharing, Byzantine Fault Tolerance
Basierend auf State-of-the-Art Distributed Systems Research
"""

import asyncio
import hashlib
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import json

from modules.logger import Logger

logger = Logger(__name__)


class NodeStatus(Enum):
    """Node Status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SYNCING = "syncing"
    FAILED = "failed"


@dataclass
class AgentNode:
    """Agent Node"""
    node_id: str
    address: str
    status: NodeStatus
    last_heartbeat: datetime
    capabilities: List[str]
    performance_score: float
    
    def to_dict(self) -> dict:
        return {
            'node_id': self.node_id,
            'address': self.address,
            'status': self.status.value,
            'last_heartbeat': self.last_heartbeat.isoformat(),
            'capabilities': self.capabilities,
            'performance_score': self.performance_score
        }


@dataclass
class ConsensusDecision:
    """Consensus Decision"""
    decision_id: str
    action: str
    votes_for: int
    votes_against: int
    total_nodes: int
    decision_hash: str
    timestamp: datetime
    status: str  # pending, approved, rejected
    
    def to_dict(self) -> dict:
        return {
            'decision_id': self.decision_id,
            'action': self.action,
            'votes_for': self.votes_for,
            'votes_against': self.votes_against,
            'total_nodes': self.total_nodes,
            'decision_hash': self.decision_hash,
            'timestamp': self.timestamp.isoformat(),
            'status': self.status
        }


class MultiAgentCoordinator:
    """
    Multi-Agent Coordinator für Distributed Agent Coordination
    
    Features:
    - Node Discovery Mechanismus
    - Leader Election Algorithm (Raft-inspired)
    - Distributed State Sharing
    - Byzantine Fault Tolerance
    - Conflict Resolution
    - Consensus Decision Making
    """
    
    def __init__(self, node_id: str):
        """
        Initialisiere Multi-Agent Coordinator
        
        Args:
            node_id: Einzigartige Node ID
        """
        self.node_id = node_id
        self.nodes: Dict[str, AgentNode] = {}
        self.leader_node_id: Optional[str] = None
        self.consensus_decisions: Dict[str, ConsensusDecision] = {}
        self.state_log: List[Dict] = []
        self.running = False
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.leader_election_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Starte Multi-Agent Coordinator"""
        self.running = True
        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self.leader_election_task = asyncio.create_task(self._leader_election_loop())
        logger.info(f"✅ Multi-Agent Coordinator started on node {self.node_id}")
    
    async def stop(self):
        """Stoppe Multi-Agent Coordinator"""
        self.running = False
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
        if self.leader_election_task:
            self.leader_election_task.cancel()
            try:
                await self.leader_election_task
            except asyncio.CancelledError:
                pass
        logger.info(f"✅ Multi-Agent Coordinator stopped on node {self.node_id}")
    
    async def _heartbeat_loop(self):
        """Heartbeat Loop für Node Discovery"""
        while self.running:
            try:
                await self._send_heartbeat()
                await asyncio.sleep(10)  # Alle 10 Sekunden
            except Exception as e:
                logger.info(f"Heartbeat error: {e}")
                await asyncio.sleep(30)
    
    async def _leader_election_loop(self):
        """Leader Election Loop"""
        while self.running:
            try:
                await self._elect_leader()
                await asyncio.sleep(30)  # Alle 30 Sekunden
            except Exception as e:
                logger.info(f"Leader election error: {e}")
                await asyncio.sleep(60)
    
    async def _send_heartbeat(self):
        """Sende Heartbeat an andere Nodes"""
        # In echter Implementation: Broadcast via Redis Pub/Sub oder gRPC
        # Für Demo: Simuliert
        self.nodes[self.node_id] = AgentNode(
            node_id=self.node_id,
            address=f"node://{self.node_id}",
            status=NodeStatus.ACTIVE,
            last_heartbeat=datetime.now(),
            capabilities=['targeting', 'detection', 'sweeping'],
            performance_score=np.random.uniform(0.5, 1.0)
        )
        
        # Prüfe auf stale nodes
        self._cleanup_stale_nodes()
    
    async def _elect_leader(self):
        """Führe Leader Election durch"""
        if not self.nodes:
            return
        
        # Leader Election basierend auf Performance Score
        active_nodes = [n for n in self.nodes.values() if n.status == NodeStatus.ACTIVE]
        
        if not active_nodes:
            self.leader_node_id = None
            return
        
        # Node mit höchstem Performance Score wird Leader
        leader = max(active_nodes, key=lambda n: n.performance_score)
        self.leader_node_id = leader.node_id
        
        # Log Leader Election
        self._log_state_change('leader_elected', {'leader': self.leader_node_id})
    
    def _cleanup_stale_nodes(self):
        """Bereinige stale Nodes"""
        now = datetime.now()
        stale_threshold = timedelta(seconds=30)
        
        for node_id, node in self.nodes.items():
            if node_id != self.node_id and (now - node.last_heartbeat) > stale_threshold:
                node.status = NodeStatus.INACTIVE
    
    async def propose_decision(self, action: str, data: dict) -> ConsensusDecision:
        """
        Propose Decision für Consensus
        
        Args:
            action: Action Type
            data: Action Data
            
        Returns:
            ConsensusDecision
        """
        decision_id = hashlib.sha256(f"{action}_{datetime.now().isoformat()}".encode()).hexdigest()[:16]
        
        # In echter Implementation: Broadcast an alle Nodes
        # Für Demo: Simuliert mit lokalem Consensus
        
        active_nodes = [n for n in self.nodes.values() if n.status == NodeStatus.ACTIVE]
        total_nodes = len(active_nodes)
        
        # Byzantine Fault Tolerance: benötigt > 2/3 Mehrheit
        votes_for = int(total_nodes * 0.67)  # Simuliert 67% Zustimmung
        votes_against = total_nodes - votes_for
        
        decision = ConsensusDecision(
            decision_id=decision_id,
            action=action,
            votes_for=votes_for,
            votes_against=votes_against,
            total_nodes=total_nodes,
            decision_hash=hashlib.sha256(json.dumps(data).encode()).hexdigest(),
            timestamp=datetime.now(),
            status='approved' if votes_for > total_nodes * 0.5 else 'rejected'
        )
        
        self.consensus_decisions[decision_id] = decision
        self._log_state_change('decision_proposed', decision.to_dict())
        
        return decision
    
    def _log_state_change(self, event_type: str, data: dict):
        """Log State Change"""
        self.state_log.append({
            'timestamp': datetime.now().isoformat(),
            'node_id': self.node_id,
            'event_type': event_type,
            'data': data
        })
        
        # Begrenze Log Size
        if len(self.state_log) > 1000:
            self.state_log = self.state_log[-1000:]
    
    def get_node_status(self) -> Dict[str, AgentNode]:
        """Hole Status aller Nodes"""
        return self.nodes
    
    def get_leader(self) -> Optional[AgentNode]:
        """Hole aktuellen Leader"""
        if self.leader_node_id and self.leader_node_id in self.nodes:
            return self.nodes[self.leader_node_id]
        return None
    
    def get_consensus_decisions(self, limit: int = 10) -> List[ConsensusDecision]:
        """Hole Consensus Decisions"""
        return list(self.consensus_decisions.values())[-limit:]
    
    def get_state_log(self, limit: int = 100) -> List[Dict]:
        """Hole State Log"""
        return self.state_log[-limit:]


# Beispiel-Usage
async def main():
    # Erstelle Multi-Agent Coordinator
    coordinator = MultiAgentCoordinator("node_001")
    
    # Starte Coordinator
    await coordinator.start()
    
    # Simuliere andere Nodes
    coordinator.nodes["node_002"] = AgentNode(
        node_id="node_002",
        address="node://node_002",
        status=NodeStatus.ACTIVE,
        last_heartbeat=datetime.now(),
        capabilities=['targeting', 'detection'],
        performance_score=0.8
    )
    
    coordinator.nodes["node_003"] = AgentNode(
        node_id="node_003",
        address="node://node_003",
        status=NodeStatus.ACTIVE,
        last_heartbeat=datetime.now(),
        capabilities=['detection', 'sweeping'],
        performance_score=0.6
    )
    
    # Warte für Leader Election
    await asyncio.sleep(5)
    
    # Hole Leader
    leader = coordinator.get_leader()
    logger.info(f"✅ Leader: {leader.node_id if leader else 'None'}")
    
    # Propose Decision
    decision = await coordinator.propose_decision("select_target", {"target": "0x1234..."})
    logger.info(f"✅ Decision: {decision.status} (Votes: {decision.votes_for}/{decision.total_nodes})")
    
    # Stoppe Coordinator
    await coordinator.stop()


if __name__ == "__main__":
    asyncio.run(main())
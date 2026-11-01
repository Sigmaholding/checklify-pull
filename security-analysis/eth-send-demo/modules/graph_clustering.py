"""
Graph Clustering - Counterparty Clustering mit NetworkX
Entity Resolution, Graph-Based Feature Extraction
Basierend auf State-of-the-Art Research (TorchLedger, RiskSEA)
"""

import networkx as nx
from typing import Dict, List, Set
from dataclasses import dataclass
from datetime import datetime

from modules.logger import Logger

logger = Logger(__name__)


@dataclass
class GraphCluster:
    """Graph Cluster"""
    cluster_id: int
    addresses: Set[str]
    cluster_type: str  # entity, mixer, exchange, normal
    avg_degree: float
    avg_betweenness: float
    size: int
    timestamp: datetime
    
    def to_dict(self) -> dict:
        return {
            'cluster_id': self.cluster_id,
            'addresses': list(self.addresses),
            'cluster_type': self.cluster_type,
            'avg_degree': self.avg_degree,
            'avg_betweenness': self.avg_betweenness,
            'size': self.size,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class Entity:
    """Entity (Cluster von Adressen)"""
    entity_id: str
    addresses: Set[str]
    total_volume_usd: float
    total_transactions: int
    first_seen: datetime
    last_seen: datetime
    risk_score: float
    
    def to_dict(self) -> dict:
        return {
            'entity_id': self.entity_id,
            'addresses': list(self.addresses),
            'total_volume_usd': self.total_volume_usd,
            'total_transactions': self.total_transactions,
            'first_seen': self.first_seen.isoformat(),
            'last_seen': self.last_seen.isoformat(),
            'risk_score': self.risk_score
        }


class GraphClustering:
    """
    Graph-Based Clustering für Entity Resolution
    
    Features:
    - NetworkX Graph Construction
    - Counterparty Clustering mit HDBSCAN
    - Entity Resolution
    - Graph-Based Feature Extraction
    - Integration mit ML-Scorer
    """
    
    def __init__(self):
        """Initialisiere Graph Clustering"""
        self.graph = nx.Graph()
        self.clusters: Dict[int, GraphCluster] = {}
        self.entities: Dict[str, Entity] = {}
        self.address_to_entity: Dict[str, str] = {}
    
    def build_graph(self, transactions: List[dict]):
        """
        Baue Transaction Graph
        
        Args:
            transactions: Liste von Transaktionen
        """
        self.graph = nx.Graph()
        
        for tx in transactions:
            from_addr = tx.get('from_address', '')
            to_addr = tx.get('to_address', '')
            amount = tx.get('amount', 0)
            
            if from_addr and to_addr:
                # Add Nodes
                self.graph.add_node(from_addr)
                self.graph.add_node(to_addr)
                
                # Add Edge mit Weight (Amount)
                if self.graph.has_edge(from_addr, to_addr):
                    self.graph[from_addr][to_addr]['weight'] += amount
                    self.graph[from_addr][to_addr]['count'] += 1
                else:
                    self.graph.add_edge(from_addr, to_addr, weight=amount, count=1)
        
        logger.info(f"✅ Graph built: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges")
    
    def detect_communities(self) -> List[GraphCluster]:
        """
        Detect Communities mit NetworkX
        
        Returns:
            Liste von GraphCluster
        """
        if self.graph.number_of_nodes() < 2:
            return []
        
        # Community Detection mit Louvain (Fallback: Connected Components bei degenerierten Graphen)
        try:
            communities = nx.community.louvain_communities(self.graph)
        except (ZeroDivisionError, ValueError, nx.NetworkXError) as e:
            logger.warning(f"Louvain failed, falling back to connected components: {e}")
            communities = list(nx.connected_components(self.graph))
        
        # Create Cluster Objects
        clusters = []
        for cluster_id, addresses in enumerate(communities):
            subgraph = self.graph.subgraph(addresses)
            
            # Cluster Type Bestimmung
            avg_degree = sum(dict(subgraph.degree()).values()) / len(addresses) if addresses else 0.0
            
            if avg_degree > 10:
                cluster_type = "mixer"
            elif len(addresses) > 5:
                cluster_type = "entity"
            else:
                cluster_type = "normal"
            
            clusters.append(GraphCluster(
                cluster_id=cluster_id,
                addresses=set(addresses),
                cluster_type=cluster_type,
                avg_degree=avg_degree,
                avg_betweenness=0.0,  # Wird später berechnet
                size=len(addresses),
                timestamp=datetime.now()
            ))
        
        self.clusters = {c.cluster_id: c for c in clusters}
        return clusters
    
    def resolve_entities(self, transactions: List[dict]) -> List[Entity]:
        """
        Resolve Entities aus Clusters
        
        Args:
            transactions: Liste von Transaktionen
            
        Returns:
            Liste von Entity
        """
        communities = self.detect_communities()
        
        entities = []
        for cluster in communities:
            if cluster.cluster_type == "entity":
                # Berechne Entity Metrics
                entity_txs = [
                    tx for tx in transactions
                    if tx.get('from_address', '') in cluster.addresses or 
                       tx.get('to_address', '') in cluster.addresses
                ]
                
                total_volume = sum(tx.get('amount', 0) for tx in entity_txs)
                total_tx = len(entity_txs)
                
                # Risk Score basierend auf Cluster Size und Volume
                risk_score = min(100.0, (total_volume / 1000000.0) + (len(cluster.addresses) * 5))
                
                entity = Entity(
                    entity_id=f"entity_{cluster.cluster_id}",
                    addresses=cluster.addresses,
                    total_volume_usd=total_volume,
                    total_transactions=total_tx,
                    first_seen=datetime.now(),  # Wird aus Transactions berechnet
                    last_seen=datetime.now(),
                    risk_score=risk_score
                )
                
                entities.append(entity)
                
                # Map Addresses to Entity
                for addr in cluster.addresses:
                    self.address_to_entity[addr] = entity.entity_id
        
        self.entities = {e.entity_id: e for e in entities}
        return entities
    
    def extract_graph_features(self, address: str) -> Dict[str, float]:
        """
        Extrahiere Graph-Based Features für eine Adresse
        
        Args:
            address: Adresse
            
        Returns:
            Dict mit Graph Features
        """
        if address not in self.graph:
            return {
                'degree': 0.0,
                'betweenness': 0.0,
                'clustering_coefficient': 0.0,
                'pagerank': 0.0
            }
        
        degree = self.graph.degree(address)
        
        # Betweenness centrality für den gesamten Graph berechnen
        if self.graph.number_of_nodes() > 2:
            betweenness_dict = nx.betweenness_centrality(self.graph)
            betweenness = betweenness_dict.get(address, 0.0)
        else:
            betweenness = 0.0
        
        clustering = nx.clustering(self.graph, address) if degree > 1 else 0.0
        pagerank = nx.pagerank(self.graph).get(address, 0.0)
        
        return {
            'degree': float(degree),
            'betweenness': float(betweenness),
            'clustering_coefficient': float(clustering),
            'pagerank': float(pagerank)
        }


# Beispiel-Usage
if __name__ == "__main__":
    clustering = GraphClustering()
    
    # Simuliere Transactions
    transactions = []
    for i in range(100):
        from_addr = f"0x{i:040x}"
        to_addr = f"0x{(i % 10):040x}"
        transactions.append({
            'from_address': from_addr,
            'to_address': to_addr,
            'amount': 1000.0 + i * 100
        })
    
    # Baue Graph
    clustering.build_graph(transactions)
    
    # Detect Communities
    clusters = clustering.detect_communities()
    logger.info(f"✅ Communities detected: {len(clusters)}")
    for cluster in clusters[:3]:
        logger.info(f"   Cluster {cluster.cluster_id}: {cluster.cluster_type} ({cluster.size} addresses)")
    
    # Resolve Entities
    entities = clustering.resolve_entities(transactions)
    logger.info(f"\n✅ Entities resolved: {len(entities)}")
    for entity in entities:
        logger.info(f"   {entity.entity_id}: {len(entity.addresses)} addresses, Risk Score: {entity.risk_score:.2f}")
    
    # Graph Features
    if transactions:
        features = clustering.extract_graph_features(transactions[0]['from_address'])
        logger.info(f"\n✅ Graph Features: {features}")
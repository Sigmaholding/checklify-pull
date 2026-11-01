"""
Similarity Engine - Adressvergleich für Vanity-Matching
Prefix/Suffix matching, Levenshtein distance, Unicode-Homoglyph detection
"""

from typing import List, Tuple
from dataclasses import dataclass
from difflib import SequenceMatcher

from modules.logger import Logger

logger = Logger(__name__)


@dataclass
class SimilarityResult:
    """Ergebnis eines Adressvergleichs"""
    address1: str
    address2: str
    prefix_match: int
    suffix_match: int
    levenshtein_distance: int
    levenshtein_similarity: float
    visual_similarity: float
    has_homoglyphs: bool
    homoglyph_details: List[str]
    overall_score: float
    
    def is_lookalike(self, threshold: float = 0.7) -> bool:
        """Prüfe ob es sich um ein Lookalike handelt"""
        return self.overall_score >= threshold


@dataclass
class MatchPattern:
    """Pattern für Vanity-Matching"""
    prefix: str
    suffix: str
    prefix_length: int
    suffix_length: int
    total_match_length: int
    difficulty_score: float  # Höher = schwieriger


class SimilarityEngine:
    """
    Similarity Engine für Adressvergleich
    
    Features:
    - Prefix/Suffix matching
    - Levenshtein distance
    - Visual similarity
    - Unicode-Homoglyph detection
    - Difficulty scoring
    """
    
    # Gefährliche Homoglyph-Paare (visuell ähnlich aber unterschiedliche chars)
    HOMOGLYPH_PAIRS = {
        '0': ('O', 'ο', 'о'),  # Zero vs O vs Greek omicron vs Cyrillic o
        '1': ('l', 'I', 'і', 'ӏ'),  # One vs l vs I vs Ukrainian i vs Palochka
        '5': ('S', 'Ѕ'),  # Five vs S vs Cyrillic Dze
        '8': ('B', 'Β', 'В'),  # Eight vs B vs Greek Beta vs Cyrillic Ve
        'a': ('а', 'α'),  # a vs Cyrillic a vs Greek alpha
        'c': ('с', 'ϲ'),  # c vs Cyrillic c vs Greek final sigma
        'e': ('е', 'е'),  # e vs Cyrillic e
        'i': ('і', 'і'),  # i vs Ukrainian i
        'n': ('п'),  # n vs Cyrillic pe
        'o': ('о', 'ο'),  # o vs Cyrillic o vs Greek omicron
        'p': ('р'),  # p vs Cyrillic er
        'v': ('ν'),  # v vs Greek nu
        'w': ('ω'),  # w vs Greek omega
        'x': ('х', 'χ'),  # x vs Cyrillic ha vs Greek chi
        'y': ('у'),  # y vs Cyrillic u
    }
    
    def __init__(self):
        """Initialisiere Similarity Engine"""
        pass
        
    def compare_addresses(
        self,
        address1: str,
        address2: str
    ) -> SimilarityResult:
        """
        Vergleiche zwei Adressen auf Ähnlichkeit
        
        Args:
            address1: Erste Adresse
            address2: Zweite Adresse
            
        Returns:
            SimilarityResult mit allen Metriken
        """
        # Normalisieren
        addr1 = self._normalize_address(address1)
        addr2 = self._normalize_address(address2)
        
        # Prefix/Suffix matching
        prefix_match = self._calculate_prefix_match(addr1, addr2)
        suffix_match = self._calculate_suffix_match(addr1, addr2)
        
        # Levenshtein distance
        levenshtein_dist = self._levenshtein_distance(addr1, addr2)
        levenshtein_sim = 1.0 - (levenshtein_dist / max(len(addr1), len(addr2)))
        
        # Visual similarity
        visual_sim = self._calculate_visual_similarity(addr1, addr2)
        
        # Homoglyph detection
        has_homoglyphs, homoglyph_details = self._detect_homoglyphs(addr1, addr2)
        
        # Overall score (gewichtet)
        overall_score = (
            (prefix_match + suffix_match) * 0.4 +  # 40% weight on exact matches
            levenshtein_sim * 0.3 +  # 30% weight on edit distance
            visual_sim * 0.2 +  # 20% weight on visual similarity
            (1.0 if has_homoglyphs else 0.0) * 0.1  # 10% weight on homoglyphs
        )
        
        return SimilarityResult(
            address1=address1,
            address2=address2,
            prefix_match=prefix_match,
            suffix_match=suffix_match,
            levenshtein_distance=levenshtein_dist,
            levenshtein_similarity=levenshtein_sim,
            visual_similarity=visual_sim,
            has_homoglyphs=has_homoglyphs,
            homoglyph_details=homoglyph_details,
            overall_score=overall_score
        )
        
    def find_match_pattern(
        self,
        target_address: str,
        candidate_address: str
    ) -> MatchPattern:
        """
        Finde das Match-Pattern zwischen zwei Adressen
        
        Args:
            target_address: Zieladresse
            candidate_address: Kandidatenadresse
            
        Returns:
            MatchPattern mit Prefix/Suffix Info
        """
        target = self._normalize_address(target_address)
        candidate = self._normalize_address(candidate_address)
        
        # Prefix matching
        prefix_length = 0
        for i in range(min(len(target), len(candidate))):
            if target[i] == candidate[i]:
                prefix_length += 1
            else:
                break
                
        prefix = target[:prefix_length] if prefix_length > 0 else ""
        
        # Suffix matching
        suffix_length = 0
        for i in range(1, min(len(target), len(candidate)) + 1):
            if target[-i] == candidate[-i]:
                suffix_length += 1
            else:
                break
                
        suffix = target[-suffix_length:] if suffix_length > 0 else ""
        
        # Difficulty score
        total_match = prefix_length + suffix_length
        difficulty = self._calculate_difficulty(total_match)
        
        return MatchPattern(
            prefix=prefix,
            suffix=suffix,
            prefix_length=prefix_length,
            suffix_length=suffix_length,
            total_match_length=total_match,
            difficulty_score=difficulty
        )
        
    def calculate_vanity_difficulty(
        self,
        prefix_length: int,
        suffix_length: int
    ) -> float:
        """
        Berechne Difficulty Score für Vanity-Generierung
        
        Args:
            prefix_length: Länge des Prefix-Matches
            suffix_length: Länge des Suffix-Matches
            
        Returns:
            Difficulty Score (höher = schwieriger)
        """
        total = prefix_length + suffix_length
        
        # Hex characters: 16 possibilities per position
        # Difficulty = 16^total
        # Logarithmic scale for manageable numbers
        return total * 4.0  # log2(16) = 4
        
    def find_best_lookalikes(
        self,
        target_address: str,
        candidate_addresses: List[str],
        top_n: int = 5
    ) -> List[Tuple[str, SimilarityResult]]:
        """
        Finde die besten Lookalikes aus einer Liste von Kandidaten
        
        Args:
            target_address: Zieladresse
            candidate_addresses: Liste von Kandidatenadressen
            top_n: Anzahl der Top-Ergebnisse
            
        Returns:
            Liste von (address, SimilarityResult) sortiert nach Score
        """
        results = []
        
        for candidate in candidate_addresses:
            if candidate.lower() == target_address.lower():
                continue  # Skip identical addresses
                
            similarity = self.compare_addresses(target_address, candidate)
            results.append((candidate, similarity))
            
        # Sortieren nach overall score
        results.sort(key=lambda x: x[1].overall_score, reverse=True)
        
        return results[:top_n]
        
    def _normalize_address(self, address: str) -> str:
        """Normalisiere Adresse (lowercase, 0x prefix entfernen)"""
        addr = address.lower()
        if addr.startswith('0x'):
            addr = addr[2:]
        return addr
        
    def _calculate_prefix_match(self, addr1: str, addr2: str) -> int:
        """Berechne Prefix-Match-Länge"""
        match_length = 0
        for i in range(min(len(addr1), len(addr2))):
            if addr1[i] == addr2[i]:
                match_length += 1
            else:
                break
        return match_length
        
    def _calculate_suffix_match(self, addr1: str, addr2: str) -> int:
        """Berechne Suffix-Match-Länge"""
        match_length = 0
        for i in range(1, min(len(addr1), len(addr2)) + 1):
            if addr1[-i] == addr2[-i]:
                match_length += 1
            else:
                break
        return match_length
        
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Berechne Levenshtein-Distanz"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
            
        if len(s2) == 0:
            return len(s1)
            
        previous_row = range(len(s2) + 1)
        
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                
                current_row.append(min(insertions, deletions, substitutions))
                
            previous_row = current_row
            
        return previous_row[-1]
        
    def _calculate_visual_similarity(self, addr1: str, addr2: str) -> float:
        """Berechne visuelle Ähnlichkeit"""
        # Use SequenceMatcher für basic similarity
        matcher = SequenceMatcher(None, addr1, addr2)
        return matcher.ratio()
        
    def _detect_homoglyphs(self, addr1: str, addr2: str) -> Tuple[bool, List[str]]:
        """Erkenne Unicode-Homoglyphs"""
        details = []
        has_homoglyphs = False
        
        # Vergleiche character-by-character
        for c1, c2 in zip(addr1, addr2):
            if c1 != c2:
                # Prüfe ob es ein Homoglyph-Paar ist
                for base, variants in self.HOMOGLYPH_PAIRS.items():
                    if c1 in variants and c2 in variants:
                        has_homoglyphs = True
                        details.append(f"'{c1}' vs '{c2}' (homoglyph for '{base}')")
                        break
                        
        return has_homoglyphs, details
        
    def _calculate_difficulty(self, total_match_length: int) -> float:
        """Berechne Difficulty Score"""
        return self.calculate_vanity_difficulty(
            total_match_length // 2,  # Annahme: gleichmäßige Verteilung
            total_match_length // 2
        )
        
    def is_safe_difference(
        self,
        address1: str,
        address2: str,
        min_diff_chars: int = 4
    ) -> bool:
        """
        Prüfe ob zwei Adressen sicher unterschiedlich sind
        
        Args:
            address1: Erste Adresse
            address2: Zweite Adresse
            min_diff_chars: Minimale Anzahl unterschiedlicher Characters
            
        Returns:
            True wenn sicher unterschiedlich
        """
        similarity = self.compare_addresses(address1, address2)
        
        # Prüfe auf ausreichende Unterschiede
        total_match = similarity.prefix_match + similarity.suffix_match
        if total_match >= (40 - min_diff_chars):  # 40 chars in ETH address
            return False
            
        # Prüfe auf Homoglyphs
        if similarity.has_homoglyphs:
            return False
            
        return True


# Beispiel-Usage
async def main():
    """Beispiel-Usage"""
    engine = SimilarityEngine()
    
    # Beispiel-Adressen
    addr1 = "0xB2bC30C3a8C04c6F4100b5cC76f83c547dc373b1"
    addr2 = "0xB2bC25cC4F9022CeB20fB42b123aE3a3094473b1"
    
    # Vergleichen
    result = engine.compare_addresses(addr1, addr2)
    
    logger.info(f"Comparison between {addr1[:10]}... and {addr2[:10]}...")
    logger.info(f"  Prefix match: {result.prefix_match}")
    logger.info(f"  Suffix match: {result.suffix_match}")
    logger.info(f"  Levenshtein distance: {result.levenshtein_distance}")
    logger.info(f"  Overall score: {result.overall_score:.3f}")
    logger.info(f"  Is lookalike: {result.is_lookalike()}")
    
    # Match pattern
    pattern = engine.find_match_pattern(addr1, addr2)
    logger.info(f"\nMatch pattern:")
    logger.info(f"  Prefix: {pattern.prefix} ({pattern.prefix_length} chars)")
    logger.info(f"  Suffix: {pattern.suffix} ({pattern.suffix_length} chars)")
    logger.info(f"  Difficulty: {pattern.difficulty_score:.1f}")
    
    # Best lookalikes
    candidates = [
        "0xB2bC25cC4F9022CeB20fB42b123aE3a3094473b1",
        "0xB2bC30C3a8C04c6F4100b5cC76f83c547dc373b1",  # Identical
        "0xAaAa25cC4F9022CeB20fB42b123aE3a3094473b1",
        "0xB2bC30C3a8C04c6F4100b5cC76f83c547dc373b2",  # 1 char diff
    ]
    
    best = engine.find_best_lookalikes(addr1, candidates, top_n=3)
    logger.info(f"\nBest lookalikes:")
    for addr, sim in best:
        logger.info(f"  {addr[:10]}... - Score: {sim.overall_score:.3f}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
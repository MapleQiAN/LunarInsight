"""Entity linking and alias merging service with bilingual support."""
from typing import List, Dict, Optional, Set
from models.document import Triplet
from infra.neo4j_client import neo4j_client
import re


class EntityLinker:
    """Link entities and merge aliases with intelligent concept fusion."""
    
    def __init__(self):
        # Alias dictionary for both languages
        self.alias_dict: Dict[str, str] = {}
        # Cache for recently linked concepts
        self.concept_cache: Dict[str, Dict] = {}
    
    def link_and_merge(self, triplets: List[Triplet]) -> List[Triplet]:
        """
        Link entities to existing concepts and intelligently merge into existing graph.
        
        Args:
            triplets: List of extracted triplets
            
        Returns:
            List of triplets with linked entities
        """
        linked_triplets = []
        
        for triplet in triplets:
            # Normalize subject and object
            subject_normalized = self._normalize_entity(triplet.subject)
            object_normalized = self._normalize_entity(triplet.object)
            
            # Find canonical names (merge with existing concepts)
            subject_canonical = self._find_or_merge_concept(subject_normalized)
            object_canonical = self._find_or_merge_concept(object_normalized)
            
            # Update triplet with canonical names
            triplet.subject = subject_canonical
            triplet.object = object_canonical
            
            linked_triplets.append(triplet)
        
        return linked_triplets
    
    def _normalize_entity(self, entity: str) -> str:
        """
        Normalize entity name with bilingual support.
        - Trim whitespace
        - Remove extra spaces
        - Preserve original language case
        """
        if not entity:
            return entity
        
        # Basic normalization
        normalized = entity.strip()
        # Remove multiple spaces
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Check alias dictionary
        normalized_lower = normalized.lower()
        if normalized_lower in self.alias_dict:
            return self.alias_dict[normalized_lower]
        
        return normalized
    
    def _find_or_merge_concept(self, name: str) -> str:
        """
        Intelligently find existing concept or merge with similar ones.
        Returns canonical name for graph insertion.
        
        Fusion strategy:
        1. Exact match (case-insensitive) → use existing
        2. Fuzzy match (similarity check) → merge into most similar
        3. Translation match (e.g., "知识图谱" ↔ "Knowledge Graph") → link as aliases
        4. No match → create new concept
        """
        if not name:
            return name
        
        # Check cache first
        if name in self.concept_cache:
            return self.concept_cache[name].get('canonical_name', name)
        
        # 1. Exact match (case-insensitive)
        existing = neo4j_client.find_concept_by_name(name)
        if existing:
            self.concept_cache[name] = existing['c']
            return name
        
        # 2. Find similar concepts for fuzzy matching
        similar_concepts = neo4j_client.find_similar_concepts(name, threshold=0.7)
        
        if similar_concepts:
            # Choose the best match
            best_match = self._select_best_match(name, similar_concepts)
            
            if best_match:
                canonical = best_match['c']['name']
                
                # Store alias mapping for future lookups
                self.alias_dict[name.lower()] = canonical
                
                # Add as alias in Neo4j
                neo4j_client.add_concept_alias(canonical, name)
                
                self.concept_cache[name] = best_match['c']
                print(f"🔗 链接: '{name}' → '{canonical}'")
                return canonical
        
        # 3. Check for potential translation matches (bilingual support)
        translation_match = self._find_translation_match(name)
        if translation_match:
            canonical = translation_match['name']
            self.alias_dict[name.lower()] = canonical
            neo4j_client.add_concept_alias(canonical, name)
            print(f"🌐 翻译链接: '{name}' → '{canonical}'")
            return canonical
        
        # 4. No match found - create new concept
        neo4j_client.create_concept(name)
        self.concept_cache[name] = {'name': name}
        print(f"✨ 新概念: '{name}'")
        return name
    
    def _select_best_match(self, name: str, candidates: List[Dict]) -> Optional[Dict]:
        """
        Select the best matching concept from candidates.
        
        Scoring criteria:
        - Exact substring match (high score)
        - Similar length (medium score)
        - Common prefix/suffix (low score)
        """
        if not candidates:
            return None
        
        best_score = 0.0
        best_candidate = None
        
        name_lower = name.lower()
        
        for candidate in candidates:
            candidate_name = candidate['c']['name']
            candidate_lower = candidate_name.lower()
            
            score = 0.0
            
            # Exact match (case-insensitive)
            if name_lower == candidate_lower:
                return candidate
            
            # Substring match
            if name_lower in candidate_lower or candidate_lower in name_lower:
                score += 0.8
            
            # Length similarity
            len_ratio = min(len(name), len(candidate_name)) / max(len(name), len(candidate_name))
            score += len_ratio * 0.2
            
            if score > best_score:
                best_score = score
                best_candidate = candidate
        
        # Only return if score is above threshold
        return best_candidate if best_score >= 0.7 else None
    
    def _find_translation_match(self, name: str) -> Optional[Dict]:
        """
        Find potential translation matches between Chinese and English.
        This is a simplified version - in production, use translation API or dictionary.
        """
        # Common translation pairs (expandable)
        translation_pairs = {
            # Chinese → English
            '知识图谱': 'Knowledge Graph',
            '人工智能': 'Artificial Intelligence',
            '机器学习': 'Machine Learning',
            '深度学习': 'Deep Learning',
            '神经网络': 'Neural Network',
            '自然语言处理': 'Natural Language Processing',
            '计算机视觉': 'Computer Vision',
            '数据库': 'Database',
            '算法': 'Algorithm',
            '数据结构': 'Data Structure',
            # English → Chinese (reverse lookup)
            'knowledge graph': '知识图谱',
            'artificial intelligence': '人工智能',
            'machine learning': '机器学习',
            'deep learning': '深度学习',
            'neural network': '神经网络',
            'natural language processing': '自然语言处理',
            'computer vision': '计算机视觉',
            'database': '数据库',
            'algorithm': '算法',
            'data structure': '数据结构',
        }
        
        name_lower = name.lower()
        
        # Check if name has a translation pair
        if name_lower in translation_pairs:
            translated = translation_pairs[name_lower]
            # Check if translated concept exists
            existing = neo4j_client.find_concept_by_name(translated)
            if existing:
                return existing['c']
        
        return None
    
    def add_alias(self, alias: str, canonical: str):
        """Add an alias mapping manually."""
        self.alias_dict[alias.lower()] = canonical
    
    def get_concept_stats(self) -> Dict[str, int]:
        """Get statistics about concept linking."""
        return {
            'cached_concepts': len(self.concept_cache),
            'alias_mappings': len(self.alias_dict)
        }


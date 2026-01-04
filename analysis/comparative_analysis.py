"""
Comparative Analysis Layer (Section 3.5)

This is where insight starts.

Analyses include:
- Source-to-source similarity
- Cluster formation
- Temporal drift
- Frame overlap

Output objects are derived, not stored as truth.
This layer is where experimentation lives.
"""

import sys
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
import numpy as np
import pandas as pd
from collections import defaultdict
from datetime import datetime

# Add project root to path
if __file__:
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from representation import Representation
from concept_assignment import ConceptInstance

logger = logging.getLogger(__name__)


@dataclass
class ComparisonResult:
    """
    ComparisonResult schema from architecture (section 3.5).
    
    Represents a comparative analysis result.
    """
    concept_id: str
    sources: List[str]  # Sources being compared
    metric_type: str  # 'similarity', 'cluster', 'drift', 'overlap', etc.
    values: Dict[str, Any]  # Metric values
    metadata: Dict[str, Any] = field(default_factory=dict)


class ComparativeAnalyzer:
    """
    Performs comparative analysis on representations.
    
    This layer generates insights by comparing how different sources
    represent the same concept.
    """
    
    def __init__(self):
        """Initialize comparative analyzer."""
        pass
    
    def _get_source_embeddings(
        self,
        representations: List[Representation],
        concept_instances: List[ConceptInstance],
        documents_df: pd.DataFrame
    ) -> Dict[str, List[np.ndarray]]:
        """
        Group embeddings by source.
        
        Returns: Dict mapping source_id -> list of embeddings
        """
        # Create lookups
        instance_lookup = {inst.text_segment_id: inst for inst in concept_instances}
        rep_lookup = {rep.concept_instance_id: rep for rep in representations}
        
        source_embeddings = defaultdict(list)
        
        for instance in concept_instances:
            rep = rep_lookup.get(instance.text_segment_id)
            if not rep or rep.embedding is None:
                continue
            
            # Get source from document using document_id from instance metadata
            doc_id = instance.metadata.get('document_id')
            if not doc_id:
                continue
            
            doc = documents_df[documents_df['id'] == doc_id]
            if doc.empty:
                continue
            
            source_id = doc.iloc[0]['source_id']
            source_embeddings[source_id].append(rep.embedding)
        
        return dict(source_embeddings)
    
    def calculate_source_similarity(
        self,
        representations: List[Representation],
        concept_instances: List[ConceptInstance],
        documents_df: pd.DataFrame,
        concept_id: str
    ) -> ComparisonResult:
        """
        Calculate source-to-source similarity.
        
        Compares average embeddings per source to see how similarly
        different sources represent the concept.
        
        Returns: ComparisonResult with similarity matrix
        """
        # Group embeddings by source
        source_embeddings = self._get_source_embeddings(representations, concept_instances, documents_df)
        
        if len(source_embeddings) < 2:
            logger.warning("Need at least 2 sources for similarity comparison")
            return None
        
        # Calculate average embedding per source
        source_avg_embeddings = {}
        for source_id, embeddings in source_embeddings.items():
            if embeddings:
                avg_embedding = np.mean(embeddings, axis=0)
                source_avg_embeddings[source_id] = avg_embedding
        
        # Calculate pairwise similarities
        sources = list(source_avg_embeddings.keys())
        similarity_matrix = {}
        
        for i, source1 in enumerate(sources):
            for source2 in sources[i+1:]:
                emb1 = source_avg_embeddings[source1]
                emb2 = source_avg_embeddings[source2]
                
                # Cosine similarity
                similarity = np.dot(emb1, emb2) / (
                    np.linalg.norm(emb1) * np.linalg.norm(emb2)
                )
                
                key = f"{source1} vs {source2}"
                similarity_matrix[key] = float(similarity)
        
        return ComparisonResult(
            concept_id=concept_id,
            sources=sources,
            metric_type='source_similarity',
            values=similarity_matrix,
            metadata={
                'num_sources': len(sources),
                'embeddings_per_source': {s: len(source_embeddings[s]) for s in sources}
            }
        )
    
    def analyze_lexical_patterns(
        self,
        representations: List[Representation],
        concept_instances: List[ConceptInstance],
        documents_df: pd.DataFrame,
        concept_id: str
    ) -> ComparisonResult:
        """
        Analyze lexical patterns (word frequency) per source.
        
        Shows what words each source uses when discussing the concept.
        """
        # Group keywords by source
        instance_lookup = {inst.text_segment_id: inst for inst in concept_instances}
        rep_lookup = {rep.concept_instance_id: rep for rep in representations}
        
        source_keywords = defaultdict(lambda: defaultdict(int))
        
        for instance in concept_instances:
            rep = rep_lookup.get(instance.text_segment_id)
            if not rep or not rep.keywords:
                continue
            
            # Get source from document using document_id from instance metadata
            doc_id = instance.metadata.get('document_id')
            if not doc_id:
                continue
            
            doc = documents_df[documents_df['id'] == doc_id]
            if doc.empty:
                continue
            
            source_id = doc.iloc[0]['source_id']
            
            # Count keywords
            for keyword in rep.keywords:
                source_keywords[source_id][keyword] += 1
        
        # Convert to format for comparison
        lexical_data = {}
        for source_id, keyword_counts in source_keywords.items():
            # Get top keywords
            top_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            lexical_data[source_id] = {
                'top_keywords': [kw for kw, count in top_keywords],
                'keyword_counts': dict(top_keywords)
            }
        
        return ComparisonResult(
            concept_id=concept_id,
            sources=list(source_keywords.keys()),
            metric_type='lexical_patterns',
            values=lexical_data,
            metadata={}
        )
    
    def analyze_coverage(
        self,
        concept_instances: List[ConceptInstance],
        documents_df: pd.DataFrame,
        concept_id: str
    ) -> ComparisonResult:
        """
        Analyze coverage: how many documents/segments per source discuss the concept.
        """
        # Group by source
        source_stats = defaultdict(lambda: {'documents': set(), 'segments': 0, 'avg_confidence': []})
        
        for instance in concept_instances:
            # Get source from document using document_id from instance metadata
            doc_id = instance.metadata.get('document_id')
            if not doc_id:
                continue
            
            doc = documents_df[documents_df['id'] == doc_id]
            if doc.empty:
                continue
            
            source_id = doc.iloc[0]['source_id']
            
            source_stats[source_id]['documents'].add(doc_id)
            source_stats[source_id]['segments'] += 1
            source_stats[source_id]['avg_confidence'].append(instance.confidence)
        
        # Calculate statistics
        coverage_data = {}
        for source_id, stats in source_stats.items():
            coverage_data[source_id] = {
                'document_count': len(stats['documents']),
                'segment_count': stats['segments'],
                'avg_confidence': np.mean(stats['avg_confidence']) if stats['avg_confidence'] else 0.0,
                'min_confidence': min(stats['avg_confidence']) if stats['avg_confidence'] else 0.0,
                'max_confidence': max(stats['avg_confidence']) if stats['avg_confidence'] else 0.0
            }
        
        return ComparisonResult(
            concept_id=concept_id,
            sources=list(source_stats.keys()),
            metric_type='coverage',
            values=coverage_data,
            metadata={}
        )

